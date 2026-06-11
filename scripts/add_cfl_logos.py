#!/usr/bin/env python3
"""Reinstate CFL teams in team-halo-config.json using TheSportsDB badges."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
GALLERY = ROOT / "logo-gallery.html"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_team_halo_config import (  # noqa: E402
    HALO_STRENGTH,
    analyze_logo,
    render_gallery,
    slugify,
)

# Verified working badges (TheSportsDB) + ESPN CFL team ids.
CFL = [
    ("BC Lions", "79", "https://r2.thesportsdb.com/images/media/team/badge/ysxssy1424732039.png"),
    ("Calgary Stampeders", "80", "https://r2.thesportsdb.com/images/media/team/badge/lksemj1565196917.png"),
    ("Edmonton Elks", "81", "https://r2.thesportsdb.com/images/media/team/badge/ehy8wx1770834697.png"),
    ("Hamilton Tiger-Cats", "82", "https://r2.thesportsdb.com/images/media/team/badge/qtwsuq1424727420.png"),
    ("Montreal Alouettes", "83", "https://r2.thesportsdb.com/images/media/team/badge/8m9v4n1770835125.png"),
    ("Ottawa Redblacks", "87", "https://r2.thesportsdb.com/images/media/team/badge/k8wjz71546002654.png"),
    ("Saskatchewan Roughriders", "84", "https://r2.thesportsdb.com/images/media/team/badge/xrdull1630952245.png"),
    ("Toronto Argonauts", "85", "https://r2.thesportsdb.com/images/media/team/badge/5a57ou1628555372.png"),
    ("Winnipeg Blue Bombers", "86", "https://r2.thesportsdb.com/images/media/team/badge/4bo4wj1561667273.png"),
]


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    existing = {t.get("favKey") for t in data["teams"]}

    added = 0
    for name, espn_id, url in CFL:
        fav = f"{name}|CFL"
        if fav in existing:
            continue
        visual = analyze_logo(url, None, None)
        data["teams"].append({
            "teamId": slugify(name, "CFL"),
            "favKey": fav,
            "names": [name],
            "league": "CFL",
            "espnIds": [espn_id],
            "logoUrl": url,
            "haloColor": visual["haloColor"],
            "haloStrength": HALO_STRENGTH,
            "needsContrastLift": visual["needsContrastLift"],
            "dominantColor": visual["dominantColor"],
            "secondaryColor": visual["secondaryColor"],
            "logoScale": visual["logoScale"],
        })
        added += 1

    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    GALLERY.write_text(render_gallery(data["teams"]), encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"CFL teams added: {added}")
    print(f"Total teams: {len(data['teams'])}")


if __name__ == "__main__":
    main()
