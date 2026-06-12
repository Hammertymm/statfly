#!/usr/bin/env python3
"""Refine visual fields in team-halo-config.json in place.

Unlike build_team_halo_config.py, this never touches the roster: it keeps every
team, name, id and logoUrl exactly as-is and only re-derives the presentation
fields (logoScale, needsContrastLift/Clamp, whiteLogo, nearBlack, halo colours)
from the existing logo assets. Safe to run any time; teams whose logo cannot be
fetched keep their previous values.

Usage:  python scripts/refine_team_halo.py
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median

from build_team_halo_config import (
    HALO_STRENGTH,
    analyze_image,
    fetch_bytes,
    hex_color,
    hex_lum,
    upgrade_logo_url,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"

# Last-resort halo accent for teams whose own colours are all too dark to glow.
# Keyed by full league name; mirrors LEAGUE_HALO_FALLBACK in index.html.
LEAGUE_ACCENT = {
    "NBA": "#1D428A", "WNBA": "#FA4D00", "NBL": "#FF6600", "NFL": "#013369",
    "MLB": "#041E42", "NHL": "#003E7E", "MLS": "#062F87", "CFL": "#C8102E",
    "Premier League": "#38003C", "Championship": "#0044A9", "League One": "#0046A8",
    "League Two": "#0046A8", "Women\u2019s Super League": "#38003C",
    "Scottish Premiership": "#002D5B", "La Liga": "#EE324E", "Bundesliga": "#D20515",
    "Serie A": "#008FD7", "Serie B": "#008FD7", "Ligue 1": "#091C3E",
    "Eredivisie": "#FF6200", "Primeira Liga": "#006847", "Belgian Pro League": "#E30613",
    "Swiss Super League": "#D52B1E", "Greek Super League": "#004C98",
    "S\u00fcper Lig": "#E30A17", "Russian Premier League": "#0039A6",
    "UEFA Champions League": "#0A1E5E", "UEFA Europa League": "#FF6900",
    "Brasileirao": "#009C3B", "Copa do Brasil": "#009C3B", "Copa Libertadores": "#1B7A3D",
    "Liga MX": "#006847", "Liga Profesional": "#75AADB", "A-League": "#FF6A13",
    "J1 League": "#D7000F", "Chinese Super League": "#DE2910", "Saudi Pro League": "#006C35",
    "ISL Football": "#2A6EBB", "PSL Football": "#007A33", "League of Ireland": "#169B62",
    "AFL": "#E31837", "NRL": "#00843D", "Super Rugby Pacific": "#00693E",
    "United Rugby Championship": "#00693E", "Top 14": "#003189", "Six Nations Rugby": "#1B3A6B",
    "Indian Premier League": "#19398A", "Big Bash League": "#FF1744",
    "Pakistan Super League": "#1B7A3D", "SA T20 Cricket": "#007A33",
    "ICC Cricket (ODI)": "#1B3A6B", "ICC Cricket (T20)": "#1B3A6B",
}


def brighten(hex_str: str, target: float = 0.40) -> str | None:
    """Lift a dark brand colour to a visible luminance while keeping its hue.

    Scales the RGB channels up (preserving saturation) until the brightest channel
    clips, then blends the rest of the way toward white. Returns None for true
    black/near-black where no hue can be recovered.
    """
    h = hex_color(hex_str)
    if not h:
        return None
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if max(r, g, b) < 10:
        return None

    def lum(rr: float, gg: float, bb: float) -> float:
        return (0.2126 * rr + 0.7152 * gg + 0.0722 * bb) / 255.0

    base = lum(r, g, b)
    if base <= 0:
        return None
    f = min(target / base, 255.0 / max(r, g, b))
    r, g, b = r * f, g * f, b * f
    while lum(r, g, b) < target:
        nr, ng, nb = r + (255 - r) * 0.05, g + (255 - g) * 0.05, b + (255 - b) * 0.05
        if (nr, ng, nb) == (r, g, b):
            break
        r, g, b = nr, ng, nb
    return "#{:02X}{:02X}{:02X}".format(round(r), round(g), round(b))

# Median-relative optical scaling: a logo's "weight" is the linear extent of its
# ink (sqrt of ink mass x bounding-box fill). We scale each logo toward the set's
# median weight so heavy and light crests read at a consistent size, then nudge the
# whole set slightly below 1.0 so nothing crowds its container.
SCALE_MIN, SCALE_MAX = 0.85, 1.18
MEDIAN_TARGET = 0.98


def perceived_weight(meta: dict) -> float:
    mass = max(meta.get("mass", 1.0), 0.05)
    fill = max(meta.get("fillRatio", 1.0), 0.2)
    return (mass ** 0.5) * fill


def analyze_team(team: dict) -> dict | None:
    url = team.get("logoUrl") or ""
    if not url:
        return None
    data = fetch_bytes(upgrade_logo_url(url))
    if not data:
        return None
    try:
        return analyze_image(data)
    except Exception:
        return None


def apply_meta(team: dict, meta: dict | None, scale: float | None) -> dict:
    if meta is None:
        # keep existing values, just ensure the new keys exist
        team.setdefault("needsContrastClamp", False)
        team.setdefault("whiteLogo", False)
        team.setdefault(
            "nearBlack",
            bool(team.get("needsContrastLift")) and hex_lum(team.get("haloColor")) < 0.2,
        )
        return team

    dominant = meta.get("haloColor") or team.get("dominantColor") or team.get("haloColor")
    secondary = meta.get("secondaryColor") or team.get("secondaryColor") or dominant
    halo = dominant or "#06F03C"
    if hex_lum(halo) < 0.12:
        for alt in (secondary, team.get("secondaryColor")):
            if alt and hex_lum(alt) >= 0.12:
                halo = alt
                break
    # Still too dark (both brand colours are near-black): keep the team's identity
    # by brightening its dominant hue; only a true black falls back to the league.
    if hex_lum(halo) < 0.12:
        halo = (
            brighten(dominant)
            or LEAGUE_ACCENT.get(team.get("league", ""))
            or "#06F03C"
        )

    team["haloColor"] = hex_color(halo) or team.get("haloColor")
    team["dominantColor"] = hex_color(dominant) or team.get("dominantColor")
    team["secondaryColor"] = hex_color(secondary) or team.get("secondaryColor")
    team["haloStrength"] = HALO_STRENGTH
    team["needsContrastLift"] = bool(meta.get("needsContrastLift"))
    team["needsContrastClamp"] = bool(meta.get("needsContrastClamp"))
    team["whiteLogo"] = bool(meta.get("whiteLogo"))
    dom_lum = hex_lum(team.get("dominantColor"))
    sec_lum = hex_lum(team.get("secondaryColor"))
    darkest = min(dom_lum, sec_lum)
    near_black = bool(meta.get("nearBlack") or darkest < 0.15)
    team["nearBlack"] = near_black
    if near_black and (meta.get("deepDark") or darkest < 0.12):
        team["deepDark"] = True
    else:
        team.pop("deepDark", None)
    if scale is not None:
        team["logoScale"] = scale
    return team


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    teams = config.get("teams", [])
    total = len(teams)

    # Pass 1: fetch + analyze every logo (threaded).
    metas: list[dict | None] = [None] * total
    done = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(analyze_team, t): i for i, t in enumerate(teams)}
        for fut in as_completed(futures):
            metas[futures[fut]] = fut.result()
            done += 1
            if done % 50 == 0 or done == total:
                print(f"  analyzed {done}/{total}", flush=True)

    # Median-relative scale, computed per league so a league's crests are internally
    # consistent (ink conventions vary a lot between, say, AFL and the NBA).
    by_league: dict[str, list[float]] = {}
    for t, m in zip(teams, metas):
        if m is not None:
            by_league.setdefault(t.get("league", ""), []).append(perceived_weight(m))
    league_median = {lg: median(ws) for lg, ws in by_league.items() if ws}
    global_median = median([w for ws in by_league.values() for w in ws]) or 1.0

    for t, m in zip(teams, metas):
        scale = None
        if m is not None:
            med = league_median.get(t.get("league", ""), global_median) or global_median
            raw = MEDIAN_TARGET * med / max(perceived_weight(m), 1e-3)
            scale = round(min(SCALE_MAX, max(SCALE_MIN, raw)), 2)
        apply_meta(t, m, scale)

    config["defaultHaloStrength"] = HALO_STRENGTH
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    lifts = sum(1 for t in teams if t.get("needsContrastLift"))
    clamps = sum(1 for t in teams if t.get("needsContrastClamp"))
    whites = sum(1 for t in teams if t.get("whiteLogo"))
    downs = sum(1 for t in teams if (t.get("logoScale") or 1) < 1.0)
    ups = sum(1 for t in teams if (t.get("logoScale") or 1) > 1.0)
    print(f"Done. {total} teams | lift={lifts} clamp={clamps} white={whites} "
          f"downscaled={downs} upscaled={ups}")


if __name__ == "__main__":
    main()
