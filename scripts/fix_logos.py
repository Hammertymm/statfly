#!/usr/bin/env python3
"""Targeted logo corrections for ScoreFly (data-quality audit).

Fixes four confirmed issues and rebuilds their local assets with the same
trim/fit/sharpen pipeline as optimize_logos.py:

  * San Diego Padres - swap to ESPN's dark-mode (gold) SD mark; the brown mark
    was near-invisible on the dark UI.
  * Portland Fire     - build the missing local asset (remote was already correct).
  * Toronto Tempo     - build the missing local asset (remote was already correct).
  * LA Clippers       - entry was corrupted with Lakers data (id 13 / lal.png /
    gold halo); repoint to the real Clippers crest (id 12 / lac.png) + navy halo.
"""
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
ASSET_DIR = ROOT / "assets" / "logos"
SAFE_AREA = 0.92


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read()


def trim_to_alpha(img: Image.Image) -> Image.Image:
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


def fit_square(img: Image.Image, size: int, allow_upscale: bool) -> Image.Image:
    crest = trim_to_alpha(img)
    target = int(size * SAFE_AREA)
    w, h = crest.size
    if w == 0 or h == 0:
        return img.resize((size, size), Image.Resampling.LANCZOS)
    scale = min(target / w, target / h)
    if not allow_upscale and max(w, h) >= target:
        scale = min(scale, 1.0)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    crest = crest.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(crest, ((size - nw) // 2, (size - nh) // 2), crest)
    return canvas


def sharpen(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=2))


def save_png(img: Image.Image, path: Path) -> None:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    path.write_bytes(buf.getvalue())


def build_asset(team_id: str, url: str) -> None:
    raw = Image.open(io.BytesIO(fetch(url))).convert("RGBA")
    save_png(sharpen(fit_square(raw, 512, allow_upscale=False)), ASSET_DIR / f"{team_id}.png")
    save_png(sharpen(fit_square(raw, 1024, allow_upscale=True)), ASSET_DIR / f"{team_id}@2x.png")
    print(f"  built {team_id} from {url}")


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    by_id = {t["teamId"]: t for t in cfg["teams"]}

    # 1) Padres -> gold dark-mode SD mark
    p = by_id["san-diego-padres-mlb"]
    p["logoUrl"] = "https://a.espncdn.com/i/teamlogos/mlb/500-dark/sd.png"
    p["needsContrastLift"] = False
    p["nearBlack"] = False
    p["deepDark"] = False
    build_asset("san-diego-padres-mlb", p["logoUrl"])

    # 2) Portland Fire -> build missing local asset (remote already correct)
    build_asset("portland-fire-wnba", by_id["portland-fire-wnba"]["logoUrl"])

    # 3) Toronto Tempo -> build missing local asset (remote already correct)
    build_asset("toronto-tempo-wnba", by_id["toronto-tempo-wnba"]["logoUrl"])

    # 4) LA Clippers -> repair corrupted (Lakers) entry
    c = by_id["los-angeles-clippers-nba"]
    c["espnIds"] = ["12"]
    c["logoUrl"] = "https://a.espncdn.com/i/teamlogos/nba/500/lac.png"
    c["haloColor"] = "#1D428A"
    c["dominantColor"] = "#1D428A"
    c["secondaryColor"] = "#C8102E"
    c["needsContrastLift"] = True
    c["nearBlack"] = True
    build_asset("los-angeles-clippers-nba", c["logoUrl"])

    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Updated team-halo-config.json")


if __name__ == "__main__":
    main()
