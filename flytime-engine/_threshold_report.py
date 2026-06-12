"""One-off threshold recommendation report."""
from flytime_engine.config import LEAGUES
from flytime_engine.db import Database
from flytime_engine.flytime import FlyTimeEngine
from flytime_engine.threshold_engine import ThresholdEngine

db = Database()
engine = FlyTimeEngine()
engine.load_all(LEAGUES)
te = ThresholdEngine(db, engine)
results = te.evaluate_all("v1")

changes = []
for r in sorted(results, key=lambda x: x.get("league", "")):
    cur = r.get("current_threshold")
    rec = r.get("recommended_threshold")
    if cur is None or rec is None:
        continue
    delta = rec - cur
    if abs(delta) >= 1:
        changes.append({**r, "delta": delta})

print("=== RECOMMENDED CHANGES (delta >= 1) ===")
for c in sorted(changes, key=lambda x: -abs(x["delta"])):
    sign = "+" if c["delta"] > 0 else ""
    tag = c.get("tag") or "?"
    print(
        f"{tag:4s} {c['league']:22s} {c['current_threshold']:>3.0f} -> "
        f"{c['recommended_threshold']:>3.0f} ({sign}{c['delta']:.0f})  "
        f"conv={c['conversion_pct']:.1f}%  Y={c['yellow_flies']} R={c['red_flies']}  "
        f"FP={c['false_positives']} FN={c['false_negatives']}"
    )

print()
print(f"Total leagues evaluated: {len(results)}")
print(f"Leagues with recommended change: {len(changes)}")
print(f"Leagues unchanged: {len(results) - len(changes)}")
