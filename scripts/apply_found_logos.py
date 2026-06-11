#!/usr/bin/env python3
"""Apply ESPN-located logos (from search_missing.py) to team-halo-config.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
GALLERY = ROOT / "logo-gallery.html"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_team_halo_config import HALO_STRENGTH, analyze_logo, upgrade_logo_url, render_gallery  # noqa: E402

# Verified ESPN crests located via global search. Keyed by "Name|League".
FOUND: dict[str, tuple[str, str]] = {
    "FC Köln|Bundesliga": ("122", "https://a.espncdn.com/i/teamlogos/soccer/500/122.png"),
    "Changchun Yatai|Chinese Super League": ("8225", "https://a.espncdn.com/i/teamlogos/soccer/500/8225.png"),
    "Meizhou Hakka|Chinese Super League": ("21507", "https://a.espncdn.com/i/teamlogos/soccer/500/21507.png"),
    "Lamia|Greek Super League": ("18814", "https://a.espncdn.com/i/teamlogos/soccer/500/18814.png"),
    "Hyderabad FC|ISL Football": ("20174", "https://a.espncdn.com/i/teamlogos/soccer/500/20174.png"),
    "Kolkata Knight Riders|Indian Premier League": ("335971", "https://a.espncdn.com/i/teamlogos/cricket/500/335971.png"),
    "Mumbai Indians|Indian Premier League": ("335978", "https://a.espncdn.com/i/teamlogos/cricket/500/335978.png"),
    "Sunrisers Hyderabad|Indian Premier League": ("628333", "https://a.espncdn.com/i/teamlogos/cricket/500/628333.png"),
    "Albirex Niigata|J1 League": ("8011", "https://a.espncdn.com/i/teamlogos/soccer/500/8011.png"),
    "Consadole Sapporo|J1 League": ("9249", "https://a.espncdn.com/i/teamlogos/soccer/500/9249.png"),
    "Sagan Tosu|J1 League": ("6911", "https://a.espncdn.com/i/teamlogos/soccer/500/6911.png"),
    "Shonan Bellmare|J1 League": ("6902", "https://a.espncdn.com/i/teamlogos/soccer/500/6902.png"),
    "Yokohama FC|J1 League": ("7145", "https://a.espncdn.com/i/teamlogos/soccer/500/7145.png"),
    "Morecambe|League Two": ("278", "https://a.espncdn.com/i/teamlogos/soccer/500/278.png"),
    "Mazatlán|Liga MX": ("20702", "https://a.espncdn.com/i/teamlogos/soccer/500/20702.png"),
    "Cape Town City|PSL Football": ("7100", "https://a.espncdn.com/i/teamlogos/soccer/500/7100.png"),
    "Lahore Qalandars|Pakistan Super League": ("953847", "https://a.espncdn.com/i/teamlogos/cricket/500/953847.png"),
    "Multan Sultans|Pakistan Super League": ("1117814", "https://a.espncdn.com/i/teamlogos/cricket/500/1117814.png"),
    "Peshawar Zalmi|Pakistan Super League": ("953833", "https://a.espncdn.com/i/teamlogos/cricket/500/953833.png"),
    "Quetta Gladiators|Pakistan Super League": ("953845", "https://a.espncdn.com/i/teamlogos/cricket/500/953845.png"),
    "Boavista|Primeira Liga": ("2256", "https://a.espncdn.com/i/teamlogos/soccer/500/2256.png"),
    "Chaves|Primeira Liga": ("12705", "https://a.espncdn.com/i/teamlogos/soccer/500/12705.png"),
    "Vizela|Primeira Liga": ("20995", "https://a.espncdn.com/i/teamlogos/soccer/500/20995.png"),
    "Cape Cobras|SA T20 Cricket": ("3360", "https://a.espncdn.com/i/teamlogos/cricket/500/3360.png"),
    "Abha|Saudi Pro League": ("21833", "https://a.espncdn.com/i/teamlogos/soccer/500/21833.png"),
    "Al Raed|Saudi Pro League": ("21834", "https://a.espncdn.com/i/teamlogos/soccer/500/21834.png"),
    "Hellas Verona|Serie A": ("119", "https://a.espncdn.com/i/teamlogos/soccer/500/119.png"),
    "Salernitana|Serie A": ("3240", "https://a.espncdn.com/i/teamlogos/soccer/500/3240.png"),
    "Ascoli|Serie B": ("3346", "https://a.espncdn.com/i/teamlogos/soccer/500/3346.png"),
    "Brescia|Serie B": ("108", "https://a.espncdn.com/i/teamlogos/soccer/500/108.png"),
    "Cosenza|Serie B": ("8683", "https://a.espncdn.com/i/teamlogos/soccer/500/8683.png"),
    "FeralpiSalo|Serie B": ("11140", "https://a.espncdn.com/i/teamlogos/soccer/500/11140.png"),
    "Lecco|Serie B": ("6009", "https://a.espncdn.com/i/teamlogos/soccer/500/6009.png"),
    "Pisa|Serie B": ("3956", "https://a.espncdn.com/i/teamlogos/soccer/500/3956.png"),
    "Ternana|Serie B": ("3175", "https://a.espncdn.com/i/teamlogos/soccer/500/3175.png"),
    "Yverdon|Swiss Super League": ("21538", "https://a.espncdn.com/i/teamlogos/soccer/500/21538.png"),
    "Adana Demirspor|Süper Lig": ("20765", "https://a.espncdn.com/i/teamlogos/soccer/500/20765.png"),
    "Hatayspor|Süper Lig": ("20737", "https://a.espncdn.com/i/teamlogos/soccer/500/20737.png"),
    "Pendikspor|Süper Lig": ("9104", "https://a.espncdn.com/i/teamlogos/soccer/500/9104.png"),
    "Sivasspor|Süper Lig": ("3691", "https://a.espncdn.com/i/teamlogos/soccer/500/3691.png"),
}


def apply_visual(entry: dict, logo_url: str, espn_id: str) -> None:
    visual = analyze_logo(logo_url, None, None)
    entry["logoUrl"] = upgrade_logo_url(logo_url)
    entry["espnIds"] = [espn_id] if espn_id else []
    entry["haloColor"] = visual["haloColor"]
    entry["haloStrength"] = HALO_STRENGTH
    entry["dominantColor"] = visual["dominantColor"]
    entry["secondaryColor"] = visual["secondaryColor"]
    entry["needsContrastLift"] = visual["needsContrastLift"]
    entry["logoScale"] = visual["logoScale"]


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    applied = 0
    for entry in data["teams"]:
        fav = entry.get("favKey", "")
        if fav in FOUND and not entry.get("logoUrl"):
            espn_id, url = FOUND[fav]
            apply_visual(entry, url, espn_id)
            applied += 1

    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    still = [t for t in data["teams"] if not t.get("logoUrl")]
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Applied: {applied}")
    print(f"Still missing: {len(still)}")
    for t in still:
        print(f"  - {t['names'][0]} [{t['league']}]")

    try:
        GALLERY.write_text(render_gallery(data["teams"]), encoding="utf-8")
        print(f"Gallery regenerated: {GALLERY}")
    except Exception as exc:  # noqa: BLE001
        print(f"Gallery skipped: {exc}")


if __name__ == "__main__":
    main()
