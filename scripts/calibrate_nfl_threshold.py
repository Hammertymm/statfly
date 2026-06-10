import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

JSON_PATH = Path(__file__).parent.parent / "nfl-flytime-v1.json"
THRESHOLD_CANDIDATES = [65, 68, 70, 72, 75, 78, 80, 85, 88, 90, 92, 93, 94, 95, 96, 97, 98]


def build_index(raw):
    close_rates, matchup_ratings, form_strength, margin_rating = {}, {}, {}, {}
    for r in raw["form_strengths"]:
        form_strength[r["team"]] = r["strength"]
    for r in raw["team_margin_ratings"]:
        margin_rating[r["team"]] = r["avg_margin"]
    for r in raw["matchup_ratings"]:
        a, b = r["matchup"].split(" vs ")
        matchup_ratings[f"{a}|{b}"] = matchup_ratings[f"{b}|{a}"] = r["avg_excitement"]
    for r in raw["matchup_close_rates"]:
        a, b = r["matchup"].split(" vs ")
        close_rates[f"{a}|{b}"] = close_rates[f"{b}|{a}"] = r["close_rate"]
    return close_rates, matchup_ratings, form_strength, margin_rating


def score(home, away, idx):
    close_rates, matchup_ratings, form_strength, margin_rating = idx
    key = f"{home}|{away}"
    cr = close_rates.get(key)
    mr = matchup_ratings.get(key)
    fh, fa = form_strength.get(home), form_strength.get(away)
    mh, ma = margin_rating.get(home), margin_rating.get(away)
    if None in (cr, mr, fh, fa, mh, ma):
        return None
    fb = 100 - abs(fh - fa)
    mb = 100 - abs(mh - ma)
    return cr * 0.35 + fb * 0.25 + mb * 0.25 + mr * 0.15


def main():
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    idx = build_index(raw)
    conn_games = []
    import sqlite3
    db = Path(__file__).parent / "data" / "scorefly.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT season, match_date, home_team, away_team FROM nfl_historical_matches ORDER BY match_date")
    for season, md, h, a in cur.fetchall():
        conn_games.append((season, md, h, a))
    conn.close()

    by_week = defaultdict(list)
    for season, md, h, a in conn_games:
        # NFL week bucket: games within 7-day windows per season
        by_week[f"{season}|{md[:10]}"].append((h, a))

    # Group by season into chunks of ~16 games (NFL week approximation)
    by_season = defaultdict(list)
    for season, md, h, a in conn_games:
        by_season[season].append((md, h, a))
    weeks = []
    for season, gs in by_season.items():
        gs.sort()
        for i in range(0, len(gs), 16):
            weeks.append(gs[i : i + 16])

    print(f"Weeks (16-game chunks): {len(weeks)}")
    all_scores = []
    week_scores = []
    for wk in weeks:
        ws = []
        for _, h, a in wk:
            s = score(h, a, idx)
            if s is not None:
                ws.append(s)
                all_scores.append(s)
        if ws:
            week_scores.append(ws)

    print(f"Scored fixtures: {len(all_scores)}")
    if all_scores:
        print(f"Score range: {min(all_scores):.1f} - {max(all_scores):.1f}, mean {mean(all_scores):.1f}")

    print("\nThreshold | avg flies/week | zero-week% | 2+week%")
    best = None
    for thr in THRESHOLD_CANDIDATES:
        counts = [sum(1 for s in ws if s >= thr) for ws in week_scores]
        avg = mean(counts)
        zero = 100 * sum(1 for c in counts if c == 0) / len(counts)
        twoplus = 100 * sum(1 for c in counts if c >= 2) / len(counts)
        print(f"   {thr:3}    | {avg:5.2f}           | {zero:5.1f}%    | {twoplus:5.1f}%")
        if best is None or abs(avg - 2) < abs(best[1] - 2):
            best = (thr, avg)

    print(f"\nRecommended ~2/week: threshold {best[0]} (avg {best[1]:.2f})")


if __name__ == "__main__":
    main()
