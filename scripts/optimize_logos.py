#!/usr/bin/env python3
"""Build a curated, razor-sharp local logo library for ScoreFly.

Sports APIs hand back logos of wildly varying quality (some 64px, some muddy PNGs).
This script downloads the best available source for every team in
team-halo-config.json, trims transparent margins to a consistent safe area, applies
a subtle unsharp mask so fine outlines survive on mobile, and writes small,
web-optimized crests to ../assets/logos/:
    <teamId>.webp      base tier (default 96px) - primary asset
    <teamId>@2x.webp   retina tier (default 192px)
    <teamId>.png       base-size PNG fallback for browsers without WebP

Crests render at 24-58px in the app, so a ~96px base (192px retina) keeps them
razor sharp while being roughly 10x smaller than the old 512/1024px PNGs.

By default it only writes the image assets. Pass --link to also repoint each team's
logo to the local asset (sets "localLogo" / "localLogo2x" in team-halo-config.json);
the app prefers localLogo (WebP) over the remote URL and derives the .png fallback.

Usage:
    python scripts/optimize_logos.py                 # build 96/192 WebP + PNG fallback
    python scripts/optimize_logos.py --link          # build assets + update config
    python scripts/optimize_logos.py --skip-existing # skip files already on disk
    python scripts/optimize_logos.py --size 96 --quality 82

Notes:
    - The crest is always fit to the safe area; upscaling small sources is fine here
      because the target tiers are tiny and the unsharp mask keeps edges crisp.
    - Re-runnable; use --skip-existing to only fill gaps.
"""
from __future__ import annotations

import argparse
import io
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageFilter

from build_team_halo_config import fetch_bytes, upgrade_logo_url

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
ASSET_DIR = ROOT / "assets" / "logos"
SAFE_AREA = 0.92  # fraction of canvas the trimmed crest may occupy


def trim_to_alpha(img: Image.Image) -> Image.Image:
    """Crop to the non-transparent bounding box so every asset is consistently framed."""
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    return img.crop(bbox) if bbox else img


def fit_square(img: Image.Image, size: int, *, allow_upscale: bool) -> Image.Image:
    """Center the crest on a transparent square canvas at the given safe area."""
    crest = trim_to_alpha(img)
    target = int(size * SAFE_AREA)
    w, h = crest.size
    if w == 0 or h == 0:
        return img.resize((size, size), Image.Resampling.LANCZOS)
    scale = min(target / w, target / h)
    if not allow_upscale:
        scale = min(scale, 1.0) if max(w, h) < target else scale
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    crest = crest.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(crest, ((size - nw) // 2, (size - nh) // 2), crest)
    return canvas


def sharpen(img: Image.Image) -> Image.Image:
    """Subtle unsharp mask: rescues thin strokes without looking crunchy."""
    return img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=2))


def save_webp(img: Image.Image, path: Path, quality: int) -> None:
    buf = io.BytesIO()
    # method=6 is the slowest/highest-compression encoder; exact=True preserves
    # RGB under fully-transparent pixels so the halo probe reads clean edges.
    img.save(buf, format="WEBP", quality=quality, method=6, exact=True)
    path.write_bytes(buf.getvalue())


def save_png(img: Image.Image, path: Path) -> None:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    path.write_bytes(buf.getvalue())


def process_team(
    team: dict,
    size: int,
    quality: int,
    skip_existing: bool,
) -> tuple[str, bool, bool]:
    """Write base/retina WebP + a base-size PNG fallback. Returns (id, webp_ok, png_ok)."""
    team_id = team.get("teamId") or ""
    url = team.get("logoUrl") or ""
    if not team_id or not url:
        return team_id, False, False
    out = ASSET_DIR / f"{team_id}.webp"
    out2x = ASSET_DIR / f"{team_id}@2x.webp"
    outpng = ASSET_DIR / f"{team_id}.png"
    have_all = out.exists() and out2x.exists() and outpng.exists()
    if skip_existing and have_all:
        return team_id, True, True

    data = fetch_bytes(upgrade_logo_url(url))
    if not data:
        return team_id, out.exists(), outpng.exists()
    try:
        raw = Image.open(io.BytesIO(data)).convert("RGBA")
        base = sharpen(fit_square(raw, size, allow_upscale=True))
        retina = sharpen(fit_square(raw, size * 2, allow_upscale=True))
        save_webp(base, out, quality)
        save_webp(retina, out2x, quality)
        save_png(base, outpng)
        return team_id, True, True
    except Exception:
        return team_id, out.exists(), outpng.exists()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=96, help="base tier px (retina = 2x)")
    ap.add_argument("--quality", type=int, default=82, help="WebP quality (0-100)")
    ap.add_argument("--link", action="store_true", help="repoint config to local assets")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    teams = config.get("teams", [])
    total = len(teams)

    ok: dict[str, tuple[bool, bool]] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [
            pool.submit(process_team, t, args.size, args.quality, args.skip_existing)
            for t in teams
        ]
        for fut in as_completed(futures):
            tid, webp_ok, png_ok = fut.result()
            if tid:
                ok[tid] = (webp_ok, png_ok)
            done += 1
            if done % 50 == 0 or done == total:
                print(f"  processed {done}/{total}", flush=True)

    built = sum(1 for w, _ in ok.values() if w)
    builtpng = sum(1 for _, p in ok.values() if p)
    print(
        f"Built {built}/{total} WebP (base+@2x), {builtpng} PNG fallbacks "
        f"in {ASSET_DIR.relative_to(ROOT)}"
    )

    if args.link:
        for t in teams:
            tid = t.get("teamId")
            if not tid:
                continue
            webp_ok, _ = ok.get(tid, (False, False))
            if webp_ok:
                t["localLogo"] = f"assets/logos/{tid}.webp"
                t["localLogo2x"] = f"assets/logos/{tid}@2x.webp"
        CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Updated team-halo-config.json with localLogo / localLogo2x (WebP) paths.")


if __name__ == "__main__":
    main()
