#!/usr/bin/env python3
"""List all CFL teams from TheSportsDB and verify badge URLs."""
import json
import sys
import urllib.request


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def head_ok(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=10)
        return f"OK({r.getheader('Content-Length')})"
    except Exception:  # noqa: BLE001
        return "FAIL"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = get("https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=CFL")
    teams = data.get("teams") or []
    print(f"CFL teams in TheSportsDB: {len(teams)}\n")
    for x in sorted(teams, key=lambda t: t.get("strTeam", "")):
        badge = x.get("strBadge") or x.get("strTeamBadge") or ""
        status = head_ok(badge) if badge else "NOBADGE"
        print(f"{x.get('strTeam'):28} | {status} | {badge}")


if __name__ == "__main__":
    main()
