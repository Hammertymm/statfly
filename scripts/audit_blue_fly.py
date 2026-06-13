#!/usr/bin/env python3
"""Audit Blue Fly (Y->G) conditions for a match in the fly ledger.

Usage:
  python scripts/audit_blue_fly.py --home "West Coast Eagles" --away "North Melbourne"
  python scripts/audit_blue_fly.py --ledger path/to/exported_ledger.json

Checks whether yellow (p:1), confirmed green (a:1), and blue (bf:1) are consistent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_ledger(path: Path | None) -> dict:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    print("No ledger file supplied. Export from FlyTime Lab (Export ledger) and pass --ledger.")
    return {}


def find_match(ledger: dict, home: str, away: str) -> list[tuple[str, dict]]:
    home_l = home.lower()
    away_l = away.lower()
    hits = []
    for mid, e in ledger.items():
        if not e:
            continue
        h = (e.get("h") or "").lower()
        w = (e.get("w") or "").lower()
        if home_l in h and away_l in w:
            hits.append((mid, e))
        elif home_l in w and away_l in h:
            hits.append((mid, e))
    return hits


def audit_entry(mid: str, e: dict) -> None:
    p = bool(e.get("p"))
    a = bool(e.get("a"))
    bf = bool(e.get("bf"))
    l2 = bool(e.get("l2"))
    rf = bool(e.get("rf"))
    print(f"\nMatch ID: {mid}")
    print(f"  Teams: {e.get('h')} vs {e.get('w')} ({e.get('lg')})")
    print(f"  Yellow predicted (p): {p}")
    print(f"  Confirmed green (a):  {a}")
    print(f"  Blue fly (bf):        {bf}")
    print(f"  Likely only (l2):      {l2}")
    print(f"  Red fly (rf):         {rf}")
    print(f"  Engine: {e.get('eng')}  Threshold: {e.get('thr')}  Rating: {e.get('r')}")
    if e.get("at"):
        print(f"  Achieved at: {e.get('at')}")
    if e.get("l2t"):
        print(f"  Likely at:   {e.get('l2t')}")

    if p and a and bf:
        print("  RESULT: Blue fly OK (Y->G hit)")
    elif p and l2 and not a:
        print("  RESULT: Likely green only — confirmed FlyTime never logged (common AFL Q4 gate miss)")
    elif p and not a:
        print("  RESULT: Yellow predicted but no confirmed green — game may not have reached FlyTime clutch window")
    elif a and not p:
        print("  RESULT: Green without yellow — missed prediction (ledgerBackfillPredict should reduce this)")
    elif p and a and not bf:
        print("  RESULT: BUG — yellow and green but bf=0 (ledgerAchieved regression)")
    else:
        print("  RESULT: No fly events logged for this match")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Blue Fly ledger entries")
    parser.add_argument("--ledger", type=Path, help="Exported fly ledger JSON")
    parser.add_argument("--home", default="West Coast Eagles", help="Home team substring")
    parser.add_argument("--away", default="North Melbourne", help="Away team substring")
    args = parser.parse_args()

    ledger = load_ledger(args.ledger)
    if not ledger:
        return 1

    hits = find_match(ledger, args.home, args.away)
    if not hits:
        print(f"No ledger entries matching '{args.home}' vs '{args.away}'.")
        print(f"Ledger has {len(ledger)} entries total.")
        return 1

    for mid, e in hits:
        audit_entry(mid, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
