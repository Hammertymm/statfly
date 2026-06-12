#!/usr/bin/env python3
"""Build a curated, razor-sharp local logo library for ScoreFly.

Sports APIs hand back logos of wildly varying quality (some 64px, some muddy PNGs).
This script downloads the best available source for every team in
team-halo-config.json, trims transparent margins to a consistent safe area, applies
a subtle unsharp mask so fine outlines survive on mobile, and writes high-quality
PNGs to ../assets/logos/<teamId>.png (+ optional <teamId>@2x.png for retina).

By default it only writes the image assets. Pass --link to also repoint each team's
logo to the local asset (sets "localLogo" / "localLogo2x" in team-halo-config.json);
the app prefers localLogo over the remote URL automatically.

Usage:
    python scripts/optimize_logos.py                 # build 512px assets only
    python scripts/optimize_logos.py --link          # build assets + update config
    python scripts/optimize_logos.py --link --retina # also write 1024px @2x variants
    python scripts/optimize_logos.py --skip-existing # skip files already on disk

Notes:
    - Base tier never upscales beyond the source (avoids fake sharpness at 1x).
    - Retina tier may upscale to 1024 when the source is smaller but legible.
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


def save_png(img: Image.Image, path: Path) -> None:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    path.write_bytes(buf.getvalue())


def process_team(
    team: dict,
    size: int,
    retina: bool,
    skip_existing: bool,
) -> tuple[str, bool, bool]:
    team_id = team.get("teamId") or ""
    url = team.get("logoUrl") or ""
    if not team_id or not url:
        return team_id, False, False
    out = ASSET_DIR / f"{team_id}.png"
    out2x = ASSET_DIR / f"{team_id}@2x.png"
    need_base = not (skip_existing and out.exists())
    need_2x = retina and not (skip_existing and out2x.exists())
    if not need_base and not need_2x:
        return team_id, True, out2x.exists()

    data = fetch_bytes(upgrade_logo_url(url))
    if not data:
        return team_id, out.exists(), out2x.exists()
    try:
        raw = Image.open(io.BytesIO(data)).convert("RGBA")
        ok_base = out.exists()
        ok_2x = out2x.exists()
        if need_base:
            save_png(sharpen(fit_square(raw, size, allow_upscale=False)), out)
            ok_base = True
        if need_2x:
            save_png(sharpen(fit_square(raw, size * 2, allow_upscale=True)), out2x)
            ok_2x = True
        return team_id, ok_base, ok_2x
    except Exception:
        return team_id, out.exists(), out2x.exists()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--link", action="store_true", help="repoint config to local assets")
    ap.add_argument("--retina", action="store_true", help="also write @2x (1024px) assets")
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
            pool.submit(process_team, t, args.size, args.retina, args.skip_existing)
            for t in teams
        ]
        for fut in as_completed(futures):
            tid, base_ok, x2_ok = fut.result()
            if tid:
                ok[tid] = (base_ok, x2_ok)
            done += 1
            if done % 50 == 0 or done == total:
                print(f"  processed {done}/{total}", flush=True)

    built = sum(1 for b, _ in ok.values() if b)
    built2x = sum(1 for _, x in ok.values() if x)
    print(f"Built {built}/{total} base assets, {built2x} @2x in {ASSET_DIR.relative_to(ROOT)}")

    if args.link:
        for t in teams:
            tid = t.get("teamId")
            if not tid:
                continue
            base_ok, x2_ok = ok.get(tid, (False, False))
            if base_ok:
                t["localLogo"] = f"assets/logos/{tid}.png"
            if x2_ok:
                t["localLogo2x"] = f"assets/logos/{tid}@2x.png"
            elif "localLogo2x" in t and not x2_ok:
                del t["localLogo2x"]
        CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Updated team-halo-config.json with localLogo / localLogo2x paths.")


if __name__ == "__main__":
    main()
