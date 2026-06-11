#!/usr/bin/env python3
"""Probe ESPN CDN paths for CFL team logos."""
import sys
import urllib.request

TEAMS = {
    "BC Lions": (79, "bc"),
    "Calgary Stampeders": (80, "cgy"),
    "Edmonton Elks": (81, "edm"),
    "Hamilton Tiger-Cats": (82, "ham"),
    "Montreal Alouettes": (83, "mtl"),
    "Saskatchewan Roughriders": (84, "ssk"),
    "Toronto Argonauts": (85, "tor"),
    "Winnipeg Blue Bombers": (86, "wpg"),
    "Ottawa Red Blacks": (87, "ott"),
}


def check(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=8)
        return f"OK({r.getheader('Content-Length')})"
    except Exception:
        return "404"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for name, (tid, abbr) in TEAMS.items():
        patterns = {
            "id": f"https://a.espncdn.com/i/teamlogos/cfl/500/{tid}.png",
            "abbr": f"https://a.espncdn.com/i/teamlogos/cfl/500/{abbr}.png",
            "soccer-id": f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png",
        }
        results = {k: check(u) for k, u in patterns.items()}
        ok = next((patterns[k] for k, v in results.items() if v.startswith("OK")), None)
        print(f"{name:26} {results}  -> {ok or 'NONE'}")


if __name__ == "__main__":
    main()
