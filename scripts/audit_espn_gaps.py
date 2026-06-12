#!/usr/bin/env python3
"""Find ESPN teams with no TEAMS roster match (even after alias normalization)."""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

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

# ScoreFly curated name -> ESPN-style aliases (normalized keys)
CURATED_ALIASES: dict[str, list[str]] = {
    "carlton blues": ["carlton"],
    "collingwood magpies": ["collingwood"],
    "essendon bombers": ["essendon"],
    "fremantle dockers": ["fremantle"],
    "greater western sydney giants": ["gwsgiants", "gws"],
    "gold coast suns": ["goldcoastsuns", "gold coast suns"],
    "hawthorn hawks": ["hawthorn"],
    "melbourne demons": ["melbourne"],
    "north melbourne kangaroos": ["northmelbourne"],
    "port adelaide power": ["portadelaide"],
    "st kilda saints": ["stkilda"],
    "los angeles clippers": ["laclippers"],
    "oakland athletics": ["athletics"],
    "utah hockey club": ["utahmammoth", "utah mammoth"],
    "ottawa redblacks": ["ottawaredblacks", "ottawa red blacks"],
    "wellington phoenix": ["wellingtonphoenixfc", "wellington phoenix fc"],
    "melbourne city": ["melbournecityfc", "melbourne city fc"],
    "new york red bulls": ["redbullnewyork"],
    "st louis city sc": ["stlouiscitysc", "st louis city sc"],
    "inter miami": ["intermiamicf", "inter miami cf"],
    "orlando city": ["orlandocitysc", "orlando city sc"],
    "minnesota united": ["minnesotaunitedfc"],
    "houston dynamo": ["houstondynamofc"],
    "chicago fire": ["chicagofirefc"],
    "seattle sounders": ["seattlesoundersfc"],
    "atlanta united": ["atlantaunitedfc"],
    "brighton": ["brightonhovealbion", "brighton & hove albion"],
    "bournemouth": ["afcbournemouth"],
    "wolverhampton wanderers": ["wolves"],
}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def parse_teams(text: str) -> dict[str, list[str]]:
    m = re.search(r"const TEAMS=\{([\s\S]*?)\n\};", text)
    block = m.group(1) if m else ""
    out: dict[str, list[str]] = {}
    for mm in re.finditer(
        r"(?:'((?:\\'|[^'])*)'|\"([^\"]+)\"):\s*\[([^\]]+)\]",
        block,
    ):
        league = (mm.group(1) or mm.group(2) or "").replace("\\'", "'")
        names = re.findall(r"'((?:\\'|[^'])*)'", mm.group(3))
        out[league] = [n.replace("\\'", "'") for n in names]
    return out


def espn_team_names(sport: str, league: str) -> list[str]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=500"
    req = urllib.request.Request(url, headers={"User-Agent": "ScoreFly-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=25) as res:
        data = json.loads(res.read())
    names: list[str] = []
    for sport_obj in data.get("sports", []):
        for lg in sport_obj.get("leagues", []):
            for item in lg.get("teams", []):
                t = item.get("team") or {}
                if t.get("displayName"):
                    names.append(t["displayName"])
    return names


def curated_norm_set(league: str, names: list[str]) -> set[str]:
    out: set[str] = set()
    for name in names:
        n = norm_name(name)
        out.add(n)
        for alias in CURATED_ALIASES.get(n, []):
            out.add(norm_name(alias))
    return out


def espn_matches_curated(espn_name: str, curated_norms: set[str]) -> bool:
    n = norm_name(espn_name)
    if n in curated_norms:
        return True
    # substring either way for partial matches (e.g. "carlton" in "carltonblues")
    for c in curated_norms:
        if len(c) >= 4 and (c in n or n in c):
            return True
    return False


def main() -> None:
    curated = parse_teams(INDEX.read_text(encoding="utf-8"))
    print("=== ESPN teams with NO roster match ===")
    total = 0
    for league, (sport, code) in sorted(ESPN_FEEDS.items()):
        roster = curated.get(league, [])
        norms = curated_norm_set(league, roster)
        missing = [
            n for n in espn_team_names(sport, code)
            if not espn_matches_curated(n, norms)
        ]
        if missing:
            print(f"\n{league}:")
            for name in missing:
                print(f"  - {name}")
            total += len(missing)
    print(f"\nTotal unmatched: {total}")


if __name__ == "__main__":
    main()
