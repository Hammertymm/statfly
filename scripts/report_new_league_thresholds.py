"""Report calibrated FlyTime thresholds for leagues (yellow-fly QA).

Tuning aim (see index.html FlyTime Lab):
  - Yellow fly = upcoming prediction (every FlyTime candidate should get one)
  - Green fly  = live FlyTime
  - Red fly    = finished after FlyTime (results cards)
  - Blue fly   = yellow then green (diagnostic hit — never user-facing)
  - Lower threshold when recall is low (missed greens without yellow)
  - Raise threshold when false alarms dominate (yellows that never go green)

Enable in-app monitor: open scorefly.app/?flylab=1 then Teams tab → FlyTime Lab.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

NEW_LEAGUES = [
    ("soccer-jpn-1-flytime-v1.json", "soccer|jpn.1", 96),
    ("soccer-eng-3-flytime-v1.json", "soccer|eng.3", 97),
    ("soccer-eng-4-flytime-v1.json", "soccer|eng.4", 97),
    ("soccer-chn-1-flytime-v1.json", "soccer|chn.1", 94),
    ("soccer-bel-1-flytime-v1.json", "soccer|bel.1", 88),
    ("soccer-sui-1-flytime-v1.json", "soccer|sui.1", 85),
    ("soccer-gre-1-flytime-v1.json", "soccer|gre.1", 93),
    ("soccer-ita-2-flytime-v1.json", "soccer|ita.2", 97),
    ("soccer-ksa-1-flytime-v1.json", "soccer|ksa.1", 96),
    ("soccer-rus-1-flytime-v1.json", "soccer|rus.1", 94),
    ("cfl-flytime-v1.json", "football|cfl", 70),
    ("rugby-urc-flytime-v1.json", "rugby|270557", 90),
    ("rugby-top14-flytime-v1.json", "rugby|270559", 88),
]


def main():
    cal = ROOT / "scripts" / "calibrate_flytime.py"
    print("League | Registry Key | Games | Teams | Calibrated | In App | Match")
    print("---|---|---:|---:|---:|---:|---")
    for fname, key, in_app in NEW_LEAGUES:
        path = ROOT / fname
        if not path.exists():
            print(f"{fname} | {key} | - | - | MISSING | {in_app} | NO")
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        games = raw.get("meta", {}).get("games_sampled", "?")
        teams = len(raw.get("form_strengths", []))
        out = subprocess.check_output([sys.executable, str(cal), str(path)], text=True)
        calibrated = int(out.strip().split()[-1]) if out.strip() else in_app
        match = "YES" if calibrated == in_app else "ADJUST"
        label = raw.get("meta", {}).get("sport", fname)
        print(f"{label} | {key} | {games} | {teams} | {calibrated} | {in_app} | {match}")


if __name__ == "__main__":
    main()
