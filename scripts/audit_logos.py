#!/usr/bin/env python3
"""Audit ScoreFly team logos for data-quality problems.

Detects three classes of issue:
  1. SPORT MISMATCH  - logoUrl points to a different ESPN sport than the team's
                       league actually is (e.g. a soccer club using an /afl/ crest).
  2. CROSS-TEAM DUPE - two *different* teams whose local PNG bytes are identical
                       (a wrong asset copied across teams, or a shared placeholder).
  3. MISSING ASSET   - config sets localLogo but the file is absent on disk.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
ASSET_DIR = ROOT / "assets" / "logos"

# Map an ESPN logoUrl sport segment -> the family of leagues that legitimately use it.
SPORT_BY_LEAGUE = {
    "NBA": "nba", "WNBA": "wnba", "NBL": "nbl",
    "NFL": "nfl", "NCAAF": "ncaaf", "NCAAM": "ncaam", "CFL": "cfl",
    "MLB": "mlb",
    "NHL": "nhl",
    "AFL": "afl",
    "NRL": "rugby-league",
}
# Soccer-family leagues all use the /soccer/ path; rugby union uses /rugby/.
SOCCER_HINTS = ("league", "liga", "serie", "ligue", "bundesliga", "eredivisie",
                "primeira", "super lig", "premier", "championship", "super league",
                "mls", "a-league", "uefa", "copa", "libertadores", "brasileir",
                "psl", "isl", "scottish", "profesional", "süper")
RUGBY_HINTS = ("top 14", "urc", "super rugby", "six nations", "rugby")
CRICKET_HINTS = ("icc", "ipl", "indian premier", "t20", "odi", "psl ", "sa20", "cricket")


def expected_sport(league: str) -> str | None:
    if league in SPORT_BY_LEAGUE:
        return SPORT_BY_LEAGUE[league]
    low = league.lower()
    if any(h in low for h in CRICKET_HINTS):
        return "cricket"
    if any(h in low for h in RUGBY_HINTS):
        return "rugby"
    if any(h in low for h in SOCCER_HINTS):
        return "soccer"
    return None


def url_sport(url: str) -> str | None:
    m = re.search(r"/teamlogos/([^/]+)/", url or "")
    return m.group(1) if m else None


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    teams = cfg["teams"]

    mismatches = []
    missing = []
    hash_to_teams: dict[str, list[str]] = defaultdict(list)

    for t in teams:
        tid = t.get("teamId", "")
        league = t.get("league", "")
        url = t.get("logoUrl", "")
        us = url_sport(url)
        es = expected_sport(league)
        # cricket/rugby sometimes legitimately served from /soccer/ on ESPN, so only
        # flag the unambiguous team-sport families.
        if es and us and us != es and es in ("nba", "wnba", "nfl", "mlb", "nhl", "afl"):
            mismatches.append((tid, league, es, us, url))
        elif es == "soccer" and us in ("afl", "nba", "nfl", "mlb", "nhl"):
            mismatches.append((tid, league, es, us, url))

        local = t.get("localLogo", "")
        if local:
            p = ROOT / local
            if not p.exists():
                missing.append((tid, local, url))
            else:
                h = hashlib.md5(p.read_bytes()).hexdigest()
                hash_to_teams[h].append(tid)

    # base team identity = strip trailing league qualifier for dupe judgement
    def base_id(tid: str) -> str:
        return tid

    cross = []
    for h, tids in hash_to_teams.items():
        if len(tids) < 2:
            continue
        # collapse same-club-different-competition (share a leading slug token run)
        roots = set()
        for tid in tids:
            roots.add(re.sub(r"-(nba|wnba|nfl|mlb|nhl|afl|premier-league|la-liga|serie-a|serie-b|bundesliga|ligue-1|eredivisie|primeira-liga|uefa-champions-league|uefa-europa-league|women-women-s-super-league|six-nations-rugby|super-rugby-pacific|brasileirao|copa-do-brasil|copa-libertadores|liga-profesional|indian-premier-league|pakistan-super-league|sa-t20-cricket|icc-cricket-odi|icc-cricket-t20|isl-football|psl-football|chinese-super-league|swiss-super-league|super-lig|a-league|mls|championship|league-one|league-two|nrl).*$", "", tid))
        if len(roots) > 1:
            cross.append((h, sorted(tids)))

    print("=" * 70)
    print(f"SPORT MISMATCH  ({len(mismatches)} teams) - wrong-sport logoUrl")
    print("=" * 70)
    for tid, lg, es, us, url in sorted(mismatches):
        print(f"  {tid:42s} league={lg:24s} expected /{es}/ got /{us}/")

    print()
    print("=" * 70)
    print(f"CROSS-TEAM DUPLICATE IMAGES ({len(cross)} groups) - different teams, identical bytes")
    print("=" * 70)
    for h, tids in sorted(cross, key=lambda x: x[1][0]):
        print("  " + " == ".join(tids))

    print()
    print("=" * 70)
    print(f"MISSING LOCAL ASSET ({len(missing)} teams) - localLogo set but file absent")
    print("=" * 70)
    for tid, local, url in sorted(missing):
        print(f"  {tid:42s} -> {local}  (remote: {url})")


if __name__ == "__main__":
    main()
