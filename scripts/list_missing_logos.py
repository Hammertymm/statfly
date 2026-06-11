#!/usr/bin/env python3
"""List teams with missing logoUrl in team-halo-config.json."""
import json
from collections import defaultdict
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "team-halo-config.json"
OUT = Path(__file__).resolve().parent / "missing-logos.txt"

data = json.loads(CONFIG.read_text(encoding="utf-8"))
missing = [t for t in data["teams"] if not t.get("logoUrl")]

by_league: dict[str, list[str]] = defaultdict(list)
for t in missing:
    by_league[t["league"]].append(t["names"][0])

lines = [f"Missing logos: {len(missing)} / {len(data['teams'])} teams", ""]
for lg in sorted(by_league):
    lines.append(f"{lg} ({len(by_league[lg])})")
    for n in sorted(by_league[lg]):
        lines.append(f"  - {n}")
    lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
