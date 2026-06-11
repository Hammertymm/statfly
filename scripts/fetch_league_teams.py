"""Fetch team names from ESPN scoreboard (current) + historical finals sample."""
import json
import sys
import urllib.request
from pathlib import Path

LEAGUES = [
    ("soccer", "jpn.1", "J1 League"),
    ("soccer", "eng.3", "League One"),
    ("soccer", "eng.4", "League Two"),
    ("soccer", "chn.1", "Chinese Super League"),
    ("soccer", "bel.1", "Belgian Pro League"),
    ("soccer", "sui.1", "Swiss Super League"),
    ("soccer", "gre.1", "Greek Super League"),
    ("soccer", "ita.2", "Serie B"),
    ("soccer", "ksa.1", "Saudi Pro League"),
    ("soccer", "rus.1", "Russian Premier League"),
    ("football", "cfl", "CFL"),
    ("rugby", "270557", "United Rugby Championship"),
    ("rugby", "270559", "Top 14"),
]


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read())


def teams_from_events(data):
    teams = set()
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [None])[0]
        if not comp:
            continue
        for c in comp.get("competitors", []):
            t = (c.get("team") or {}).get("displayName") or (c.get("team") or {}).get("name")
            if t:
                teams.add(t)
    return sorted(teams)


def main():
    for sport, league, label in LEAGUES:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        hist = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates=20230801-20240615"
        teams = set()
        for u in (url, hist):
            try:
                teams.update(teams_from_events(fetch(u)))
            except Exception as e:
                print(f"# {label}: skip {u}: {e}", file=sys.stderr)
        print(f"\n# {label} ({sport}/{league}) — {len(teams)} teams")
        print(json.dumps(sorted(teams), indent=2))


if __name__ == "__main__":
    main()
