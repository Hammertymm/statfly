#!/usr/bin/env python3
"""Fix BBL + ICC logos, remove CFL from team-halo-config.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_team_halo_config import analyze_logo, HALO_STRENGTH  # noqa: E402

BBL_LOGOS: dict[str, tuple[str, str]] = {
    "Adelaide Strikers": ("509667", "https://a.espncdn.com/i/teamlogos/cricket/500/509667.png"),
    "Brisbane Heat": ("509668", "https://a.espncdn.com/i/teamlogos/cricket/500/509668.png"),
    "Hobart Hurricanes": ("509669", "https://a.espncdn.com/i/teamlogos/cricket/500/509669.png"),
    "Melbourne Renegades": ("509671", "https://a.espncdn.com/i/teamlogos/cricket/500/509671.png"),
    "Melbourne Stars": ("509672", "https://a.espncdn.com/i/teamlogos/cricket/500/509672.png"),
    "Perth Scorchers": ("509670", "https://a.espncdn.com/i/teamlogos/cricket/500/509670.png"),
    "Sydney Sixers": ("509673", "https://a.espncdn.com/i/teamlogos/cricket/500/509673.png"),
    "Sydney Thunder": ("509674", "https://a.espncdn.com/i/teamlogos/cricket/500/509674.png"),
}

ICC_COUNTRY_CODES: dict[str, str] = {
    "Afghanistan": "afg",
    "Australia": "aus",
    "Bangladesh": "ban",
    "England": "eng",
    "India": "ind",
    "Ireland": "irl",
    "New Zealand": "nzl",
    "Pakistan": "pak",
    "South Africa": "rsa",
    "Sri Lanka": "sri",
    "West Indies": "wi",
    "Zimbabwe": "zim",
}


def country_logo(code: str) -> str:
    return f"https://a.espncdn.com/i/teamlogos/countries/500/{code}.png"


def apply_visual(entry: dict, logo_url: str, espn_id: str = "") -> None:
    visual = analyze_logo(logo_url, None, None)
    entry["logoUrl"] = logo_url
    entry["espnIds"] = [espn_id] if espn_id else []
    entry["haloColor"] = visual["haloColor"]
    entry["haloStrength"] = HALO_STRENGTH
    entry["dominantColor"] = visual["dominantColor"]
    entry["secondaryColor"] = visual["secondaryColor"]
    entry["needsContrastLift"] = visual["needsContrastLift"]
    entry["logoScale"] = visual["logoScale"]


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    teams = data.get("teams", [])
    out = []
    removed_cfl = 0
    fixed_bbl = 0
    fixed_icc = 0

    for entry in teams:
        league = entry.get("league", "")
        name = (entry.get("names") or [""])[0]

        if league == "CFL":
            removed_cfl += 1
            continue

        if league == "Big Bash League" and name in BBL_LOGOS:
            espn_id, url = BBL_LOGOS[name]
            apply_visual(entry, url, espn_id)
            fixed_bbl += 1

        if league.startswith("ICC Cricket") and name in ICC_COUNTRY_CODES:
            code = ICC_COUNTRY_CODES[name]
            apply_visual(entry, country_logo(code))
            fixed_icc += 1

        out.append(entry)

    data["teams"] = out
    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Removed CFL: {removed_cfl}")
    print(f"Fixed BBL: {fixed_bbl}")
    print(f"Fixed ICC: {fixed_icc}")
    print(f"Teams remaining: {len(out)}")


if __name__ == "__main__":
    main()
