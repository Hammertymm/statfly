"""Calibrate FlyTime v1 threshold for any bootstrap JSON. Target ~2 flies per week-chunk."""
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent.parent
THRESHOLDS = [65, 68, 70, 72, 75, 78, 80, 85, 88, 90, 92, 93, 94, 95, 96, 97, 98]


def build_index(raw):
    cr, mr, fs, mg = {}, {}, {}, {}
    for r in raw["form_strengths"]:
        fs[r["team"]] = r["strength"]
    for r in raw["team_margin_ratings"]:
        mg[r["team"]] = r["avg_margin"]
    for r in raw["matchup_ratings"]:
        a, b = r["matchup"].split(" vs ")
        mr[f"{a}|{b}"] = mr[f"{b}|{a}"] = r["avg_excitement"]
    for r in raw["matchup_close_rates"]:
        a, b = r["matchup"].split(" vs ")
        cr[f"{a}|{b}"] = cr[f"{b}|{a}"] = r["close_rate"]
    return cr, mr, fs, mg


def score(home, away, idx):
    cr, mr, fs, mg = idx
    key = f"{home}|{away}"
    vals = [cr.get(key), mr.get(key), fs.get(home), fs.get(away), mg.get(home), mg.get(away)]
    if any(v is None for v in vals):
        return None
    fb = 100 - abs(fs[home] - fs[away])
    mb = 100 - abs(mg[home] - mg[away])
    return cr[key] * 0.35 + fb * 0.25 + mb * 0.25 + mr[key] * 0.15


def calibrate(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    idx = build_index(raw)
    chunk = raw.get("meta", {}).get("week_chunk", 16)

    # Score all unique matchups from matchup_close_rates (home|away pairs)
    pairs = set()
    for r in raw["matchup_close_rates"]:
        a, b = r["matchup"].split(" vs ")
        pairs.add((a, b))

    scored = [(h, a, s) for h, a in pairs if (s := score(h, a, idx)) is not None]
    if not scored:
        print(f"{path.name}: no scorable pairs")
        return None

    # Simulate weeks by chunking scored fixtures
    scored.sort(key=lambda x: x[2], reverse=True)
    # Use all pairs repeated by games_played weight — approximate with sorted list chunks
    by_gp = []
    gp_map = {}
    for r in raw["matchup_close_rates"]:
        a, b = r["matchup"].split(" vs ")
        gp_map[f"{a}|{b}"] = max(gp_map.get(f"{a}|{b}", 0), r["games"])
    for h, a, s in scored:
        for _ in range(min(gp_map.get(f"{h}|{a}", 1), 4)):
            by_gp.append(s)

    weeks = [by_gp[i : i + chunk] for i in range(0, len(by_gp), chunk)]
    weeks = [w for w in weeks if w]
    scores = [s for _, _, s in scored]
    print(f"\n{path.name} ({raw['meta'].get('sport', '?')})")
    print(f"  scorable pairs: {len(scored)}, simulated weeks: {len(weeks)}")
    print(f"  score range: {min(scores):.1f}-{max(scores):.1f}, mean {mean(scores):.1f}")

    best = None
    for thr in THRESHOLDS:
        counts = [sum(1 for s in wk if s >= thr) for wk in weeks]
        if not counts:
            continue
        avg = mean(counts)
        if best is None or abs(avg - 2) < abs(best[1] - 2):
            best = (thr, avg)
    if best:
        print(f"  recommended threshold: {best[0]} (avg {best[1]:.2f}/week-chunk)")
    return best


def main():
    if len(sys.argv) < 2:
        files = sorted(ROOT.glob("*-flytime-v1.json"))
    else:
        files = [ROOT / f"{k}-flytime-v1.json" if not k.endswith(".json") else ROOT / k for k in sys.argv[1:]]
    results = {}
    for f in files:
        if f.exists():
            r = calibrate(f)
            if r:
                results[f.stem.replace("-flytime-v1", "")] = r[0]
    if results:
        print("\n=== Summary ===")
        for k, thr in sorted(results.items()):
            print(f"  {k}: {thr}")


if __name__ == "__main__":
    main()
