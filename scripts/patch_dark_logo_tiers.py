#!/usr/bin/env python3
"""Sync nearBlack/deepDark flags in team-halo-config.json from brand colours."""
from __future__ import annotations

import json
from pathlib import Path

from build_team_halo_config import hex_lum

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"


def patch_team(entry: dict) -> tuple[bool, bool]:
    if not entry.get("needsContrastLift"):
        entry.pop("deepDark", None)
        return False, False

    dom = hex_lum(entry.get("dominantColor"))
    sec = hex_lum(entry.get("secondaryColor"))
    darkest = min(dom, sec)
    near = bool(entry.get("nearBlack") or darkest < 0.15)
    deep = near and darkest < 0.12
    entry["nearBlack"] = near
    if deep:
        entry["deepDark"] = True
    else:
        entry.pop("deepDark", None)
    return near, deep


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    near_n = deep_n = 0
    deep_teams: list[str] = []
    newly_near: list[str] = []

    for entry in data.get("teams", []):
        was_near = entry.get("nearBlack", False)
        near, deep = patch_team(entry)
        if near:
            near_n += 1
        if deep:
            deep_n += 1
            deep_teams.append(f"{entry['names'][0]} ({entry['league']})")
        if near and not was_near:
            newly_near.append(f"{entry['names'][0]} ({entry['league']})")

    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Patched {len(data['teams'])} teams: nearBlack={near_n}, deepDark={deep_n}")
    if newly_near:
        print("\nNewly near-black:")
        for line in newly_near:
            print(f"  - {line}")
    print("\nDeep-dark tier:")
    for line in sorted(deep_teams):
        print(f"  - {line}")


if __name__ == "__main__":
    main()
