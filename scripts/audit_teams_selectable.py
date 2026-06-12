#!/usr/bin/env python3
"""Find teams missing from index.html TEAMS (unselectable on Teams page)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
CONFIG = ROOT / "team-halo-config.json"


def parse_teams(text: str) -> dict[str, list[str]]:
    m = re.search(r"const TEAMS=\{([\s\S]*?)\n\};", text)
    if not m:
        raise SystemExit("TEAMS block not found")
    block = m.group(1)
    out: dict[str, list[str]] = {}
    for mm in re.finditer(
        r"(?:'((?:\\'|[^'])*)'|\"([^\"]+)\"):\s*\[([^\]]+)\]",
        block,
    ):
        league = (mm.group(1) or mm.group(2) or "").replace("\\'", "'")
        names = re.findall(r"'((?:\\'|[^'])*)'", mm.group(3))
        out[league] = [n.replace("\\'", "'") for n in names]
    return out


def parse_leagues(text: str) -> set[str]:
    m = re.search(r"const LEAGUES=\{([\s\S]*?)\n\};", text)
    if not m:
        raise SystemExit("LEAGUES block not found")
    names = re.findall(r"n:'((?:\\'|[^'])*)'", m.group(1))
    return {n.replace("\\'", "'") for n in names}


ESPN_FEEDS = {
    "NFL": ("football", "nfl"),
    "NBA": ("basketball", "nba"),
    "WNBA": ("basketball", "wnba"),
    "MLB": ("baseball", "mlb"),
    "NHL": ("hockey", "nhl"),
    "MLS": ("soccer", "usa.1"),
    "CFL": ("football", "cfl"),
    "AFL": ("australian-football", "afl"),
    "NRL": ("rugby-league", "nrl"),
    "A-League": ("soccer", "aus.1"),
    "NBL": ("basketball", "nbl"),
    "Premier League": ("soccer", "eng.1"),
}


def espn_team_names(sport: str, league: str) -> list[str]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=500"
    req = urllib.request.Request(url, headers={"User-Agent": "ScoreFly-Audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            data = json.loads(res.read())
    except Exception:
        return []
    names: list[str] = []
    for sport_obj in data.get("sports", []):
        for lg in sport_obj.get("leagues", []):
            for item in lg.get("teams", []):
                t = item.get("team") or {}
                if t.get("displayName"):
                    names.append(t["displayName"])
    return names


def main() -> None:
    index = INDEX.read_text(encoding="utf-8")
    curated = parse_teams(index)
    leagues_ui = parse_leagues(index)

    halo = json.loads(CONFIG.read_text(encoding="utf-8"))["teams"]
    halo_by_league: dict[str, set[str]] = {}
    for t in halo:
        halo_by_league.setdefault(t["league"], set()).add(t["names"][0])

    print("=== In halo config but NOT in TEAMS (unselectable on Teams page) ===")
    missing_total: list[tuple[str, str]] = []
    for league in sorted(leagues_ui):
        curated_set = set(curated.get(league, []))
        in_halo = halo_by_league.get(league, set())
        missing = sorted(in_halo - curated_set)
        if missing:
            print(f"\n{league} ({len(missing)} missing):")
            for name in missing:
                print(f"  - {name}")
                missing_total.append((league, name))

    print(f"\nTotal unselectable: {len(missing_total)}")

    print("\n=== In TEAMS but NOT in halo config ===")
    extra: list[tuple[str, str]] = []
    for league in sorted(curated):
        if league not in leagues_ui:
            continue
        curated_set = set(curated[league])
        in_halo = halo_by_league.get(league, set())
        for name in sorted(curated_set - in_halo):
            extra.append((league, name))
            print(f"  {league}: {name}")
    print(f"Total extra in TEAMS only: {len(extra)}")

    print("\n=== ESPN teams missing from TEAMS (likely unselectable) ===")
    espn_missing_total = 0
    for league, (sport, code) in sorted(ESPN_FEEDS.items()):
        if league not in leagues_ui:
            continue
        espn = set(espn_team_names(sport, code))
        curated_set = set(curated.get(league, []))
        missing = sorted(espn - curated_set)
        if missing:
            print(f"\n{league} ({len(missing)} missing):")
            for name in missing:
                print(f"  - {name}")
            espn_missing_total += len(missing)
    print(f"\nTotal ESPN-missing from TEAMS: {espn_missing_total}")


if __name__ == "__main__":
    main()
