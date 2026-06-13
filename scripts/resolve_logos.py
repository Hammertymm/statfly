#!/usr/bin/env python3
"""Resolve correct crests for the nickname-collision soccer teams.

The config builder matched some clubs by nickname and grabbed a famous same-name
team's crest (e.g. Atletico Mineiro <- Atletico Madrid, Reading <- Rajasthan
Royals). This queries ESPN's per-league teams API, matches each affected club by
name, and rebuilds its local asset + config entry from the correct logo.

Cricket / rugby franchises are NOT handled here (ESPN's image CDN does not host
them reliably - that's what triggered the fallback); they're reported separately
by audit_logos.py and listed as unresolved.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
ASSET_DIR = ROOT / "assets" / "logos"
SAFE_AREA = 0.92

# teamId -> (espn league slug, [acceptable name fragments]). Also two trivial
# missing-asset rebuilds whose remote was already correct.
# teamId -> (espn league slug, [acceptable name fragments]). Slugs reflect each
# club's CURRENT division (several were relegated/promoted, so their crest now
# lives under a different league feed).
TARGETS = {
    "atletico-mineiro-brasileirao":              ("bra.1", ["atletico mg", "atletico-mg", "mineiro"]),
    "atletico-mineiro-copa-do-brasil":           ("bra.1", ["atletico mg", "atletico-mg", "mineiro"]),
    "atletico-mineiro-copa-libertadores":        ("bra.1", ["atletico mg", "atletico-mg", "mineiro"]),
    "millwall-championship":                     ("eng.2", ["millwall"]),
    "reading-league-one":                        ("eng.3", ["reading"]),
    "doncaster-rovers-league-two":               ("eng.3", ["doncaster"]),
    "forest-green-rovers-league-two":            ("eng.5", ["forest green"]),
    "sutton-united-league-two":                  ("eng.5", ["sutton united", "sutton"]),
    "clermont-ligue-1":                          ("fra.2", ["clermont"]),
    "montpellier-ligue-1":                       ("fra.2", ["montpellier"]),
    "fc-sion-swiss-super-league":                ("sui.1", ["sion"]),
    "dalian-professional-chinese-super-league":  ("chn.1", ["dalian"]),
    "new-england-revolution-mls":                ("usa.1", ["new england"]),
    "bengaluru-fc-isl-football":                 ("ind.1", ["bengaluru"]),
}
# Stragglers ESPN's per-league feed no longer lists (relegated past API coverage,
# merged, or not on the image CDN). Resolved via the global search API instead.
SEARCH_TARGETS = {
    "cittadella-serie-b":           "Cittadella",
    "portimonense-primeira-liga":   "Portimonense",
    "western-united-a-league":      "Western United",
    "supersport-united-psl-football": "SuperSport United",
    "cape-town-spurs-psl-football": "Cape Town Spurs",
    "cangzhou-mighty-lions-chinese-super-league": "Cangzhou",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read()


_cache: dict[str, list] = {}
def league_teams(slug: str) -> list:
    if slug not in _cache:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams"
        try:
            d = json.loads(fetch(url))
            _cache[slug] = d["sports"][0]["leagues"][0]["teams"]
        except Exception:
            _cache[slug] = []
    return _cache[slug]


def search_team(query: str, name_frag: str):
    """Resolve a soccer team via ESPN's global search (covers clubs whose current
    division ESPN's per-league feed doesn't expose)."""
    import urllib.parse
    url = f"https://site.web.api.espn.com/apis/common/v3/search?query={urllib.parse.quote(query)}&limit=20"
    try:
        d = json.loads(fetch(url))
    except Exception:
        return None, None
    nf = norm(name_frag)
    for it in d.get("items", []):
        if it.get("type") != "team" or it.get("sport") != "soccer":
            continue
        if nf and nf not in norm(it.get("displayName", "")):
            continue
        logos = it.get("logos") or []
        href = ""
        for lg in logos:
            if "dark" not in (lg.get("rel") or []):
                href = lg.get("href", ""); break
        href = href or (logos[0]["href"] if logos else "")
        return it.get("id", ""), href
    return None, None


def find(slug: str, frags: list[str]):
    for t in league_teams(slug):
        tm = t["team"]
        nm = norm(tm.get("displayName", "")) + " " + norm(tm.get("name", "")) + " " + norm(tm.get("shortDisplayName", ""))
        if any(norm(f) in nm for f in frags):
            logos = tm.get("logos") or []
            href = logos[0]["href"] if logos else ""
            return tm.get("id", ""), href
    return None, None


def trim(img):
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


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
    c.paste(crest, ((size - nw) // 2, (size - nh) // 2), crest)
    return c


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

    for tid, (slug, frags) in TARGETS.items():
        if tid not in by_id:
            failed.append((tid, "no config entry")); continue
        eid, href = find(slug, frags)
        if not href:
            failed.append((tid, f"no ESPN match in {slug}")); continue
        try:
            build(tid, href)
            t = by_id[tid]
            t["logoUrl"] = href
            if eid:
                t["espnIds"] = [str(eid)]
            resolved.append((tid, eid, href))
        except Exception as e:
            failed.append((tid, f"build error: {e}"))

    # stragglers via global search
    for tid, query in SEARCH_TARGETS.items():
        if tid not in by_id:
            failed.append((tid, "no config entry")); continue
        eid, href = search_team(query, query.split()[0] if tid.startswith("cangzhou") else query)
        if not href:
            failed.append((tid, f"no search match for '{query}'")); continue
        try:
            build(tid, href)
            t = by_id[tid]
            t["logoUrl"] = href
            if eid:
                t["espnIds"] = [str(eid)]
            resolved.append((tid, eid, href))
        except Exception as e:
            failed.append((tid, f"build error: {e}"))

    # trivial missing-asset rebuilds (remote already correct)
    for tid in ["auckland-fc-a-league", "san-diego-fc-mls"]:
        if tid in by_id:
            try:
                build(tid, by_id[tid]["logoUrl"]); resolved.append((tid, "(existing)", by_id[tid]["logoUrl"]))
            except Exception as e:
                failed.append((tid, f"build error: {e}"))

    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"RESOLVED ({len(resolved)}):")
    for tid, eid, href in resolved:
        print(f"  {tid:44s} id={eid}  {href}")
    print(f"\nFAILED ({len(failed)}):")
    for tid, why in failed:
        print(f"  {tid:44s} {why}")


if __name__ == "__main__":
    main()
