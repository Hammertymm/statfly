#!/usr/bin/env python3
"""Resolve correct crests for the cricket franchises + the Waratahs that the
config builder nickname-matched to famous teams (Sacramento Kings, Miami
Dolphins, NY Giants, etc.). Uses ESPN's global search, filtered to the right
sport, and rebuilds each local asset + config entry from the proper logo.
"""
from __future__ import annotations

import io
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
ASSET_DIR = ROOT / "assets" / "logos"
SAFE_AREA = 0.92

# teamId -> (query, sport, name-fragment-that-must-appear)
TARGETS = {
    "chennai-super-kings-indian-premier-league":            ("Chennai Super Kings", "cricket", "chennai"),
    "delhi-capitals-indian-premier-league":                 ("Delhi Capitals", "cricket", "delhi capitals"),
    "gujarat-titans-indian-premier-league":                 ("Gujarat Titans", "cricket", "gujarat"),
    "lucknow-super-giants-indian-premier-league":           ("Lucknow Super Giants", "cricket", "lucknow"),
    "punjab-kings-indian-premier-league":                   ("Punjab Kings", "cricket", "punjab"),
    "royal-challengers-bengaluru-indian-premier-league":    ("Royal Challengers Bengaluru", "cricket", "royal challengers"),
    "islamabad-united-pakistan-super-league":               ("Islamabad United", "cricket", "islamabad"),
    "karachi-kings-pakistan-super-league":                  ("Karachi Kings", "cricket", "karachi"),
    "dolphins-sa-t20-cricket":                              ("Dolphins", "cricket", "dolphins"),
    "knights-sa-t20-cricket":                               ("Knights", "cricket", "knights"),
    "lions-sa-t20-cricket":                                 ("Lions", "cricket", "lions"),
    "titans-sa-t20-cricket":                                ("Titans", "cricket", "titans"),
    "warriors-sa-t20-cricket":                              ("Warriors", "cricket", "warriors"),
    "waratahs-super-rugby-pacific":                         ("NSW Waratahs", "rugby", "waratahs"),
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=25).read()


def search(query: str, sport: str, frag: str):
    url = f"https://site.web.api.espn.com/apis/common/v3/search?query={urllib.parse.quote(query)}&limit=25"
    for attempt in range(3):
        try:
            d = json.loads(fetch(url)); break
        except Exception:
            time.sleep(2)
    else:
        return None, None
    nf = norm(frag)
    # exclude women's sides unless the team is a women's side
    for it in d.get("items", []):
        if it.get("type") != "team" or it.get("sport") != sport:
            continue
        dn = norm(it.get("displayName", ""))
        if "women" in dn:
            continue
        if nf and nf not in dn:
            continue
        logos = it.get("logos") or []
        if not logos:
            continue
        href = ""
        for lg in logos:
            if "dark" not in (lg.get("rel") or []):
                href = lg.get("href", ""); break
        href = href or logos[0]["href"]
        return it.get("id", ""), href
    return None, None


def trim(img):
    bbox = img.split()[-1].getbbox(); return img.crop(bbox) if bbox else img


def fit_square(img, size, allow_upscale):
    crest = trim(img); target = int(size * SAFE_AREA); w, h = crest.size
    if not w or not h:
        return img.resize((size, size), Image.Resampling.LANCZOS)
    scale = min(target / w, target / h)
    if not allow_upscale and max(w, h) >= target:
        scale = min(scale, 1.0)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    crest = crest.resize((nw, nh), Image.Resampling.LANCZOS)
    c = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c.paste(crest, ((size - nw) // 2, (size - nh) // 2), crest); return c


def sharpen(img):
    return img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=2))


def save(img, path):
    buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True); path.write_bytes(buf.getvalue())


def build(team_id, url):
    raw = Image.open(io.BytesIO(fetch(url))).convert("RGBA")
    save(sharpen(fit_square(raw, 512, False)), ASSET_DIR / f"{team_id}.png")
    save(sharpen(fit_square(raw, 1024, True)), ASSET_DIR / f"{team_id}@2x.png")


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    by_id = {t["teamId"]: t for t in cfg["teams"]}
    resolved, failed = [], []
    for tid, (q, sport, frag) in TARGETS.items():
        if tid not in by_id:
            failed.append((tid, "no config entry")); continue
        eid, href = search(q, sport, frag)
        if not href:
            failed.append((tid, f"no {sport} match for '{q}'")); continue
        try:
            build(tid, href)
            t = by_id[tid]; t["logoUrl"] = href
            if eid:
                t["espnIds"] = [str(eid)]
            resolved.append((tid, eid, href))
        except Exception as e:
            failed.append((tid, f"build error: {e}"))
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RESOLVED ({len(resolved)}):")
    for tid, eid, href in resolved:
        print(f"  {tid:50s} id={eid}  {href}")
    print(f"\nFAILED ({len(failed)}):")
    for tid, why in failed:
        print(f"  {tid:50s} {why}")


if __name__ == "__main__":
    main()
