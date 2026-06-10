import json
import sqlite3
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / "afl-flytime-v1.json"
DB = Path(__file__).parent / "data" / "scorefly.db"
THRESHOLD = 70

AFL_RESEARCH_NAMES = {
    "North Melbourne Kangaroos": "North Melbourne",
    "Port Adelaide Power": "Port Adelaide",
    "Carlton Blues": "Carlton",
    "Collingwood Magpies": "Collingwood",
    "Essendon Bombers": "Essendon",
    "Fremantle Dockers": "Fremantle",
    "Gold Coast Suns": "Gold Coast SUNS",
    "Greater Western Sydney Giants": "GWS GIANTS",
    "Hawthorn Hawks": "Hawthorn",
    "Richmond Tigers": "Richmond",
    "St Kilda Saints": "St Kilda",
    "Melbourne Demons": "Melbourne",
}


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


def to_research(name):
    return AFL_RESEARCH_NAMES.get(name, name)


def explain(home_app, away_app, idx, verbose=True):
    home, away = to_research(home_app), to_research(away_app)
    close_rates, matchup_ratings, form_strength, margin_rating = idx
    key = f"{home}|{away}"
    cr = close_rates.get(key)
    mr = matchup_ratings.get(key)
    fh, fa = form_strength.get(home), form_strength.get(away)
    mh, ma = margin_rating.get(home), margin_rating.get(away)

    if verbose:
        print(f"\n{'='*60}")
        print(f"{home_app} vs {away_app}")
        print(f"Research lookup: {home} vs {away}")
        print(f"  close_rate (35%):           {cr}")
        print(f"  matchup_rating (15%):       {mr}")
        print(f"  form_strength home/away:    {fh} / {fa}")
        print(f"  margin_rating home/away:    {mh} / {ma}")

    if None in (cr, mr, fh, fa, mh, ma):
        if verbose:
            print("  MISSING DATA -> no yellow fly")
        return None

    fb = 100 - abs(fh - fa)
    mb = 100 - abs(mh - ma)
    score = cr * 0.35 + fb * 0.25 + mb * 0.25 + mr * 0.15

    if verbose:
        print(f"  form_balance (25%):         100 - |{fh}-{fa}| = {fb}")
        print(f"  margin_balance (25%):       100 - |{mh}-{ma}| = {mb}")
        print(f"  FLYSCORE = {cr}*0.35 + {fb}*0.25 + {mb}*0.25 + {mr}*0.15")
        print(f"         = {cr*0.35:.3f} + {fb*0.25:.3f} + {mb*0.25:.3f} + {mr*0.15:.3f}")
        print(f"         = {score:.2f}")
        flag = "YES - yellow fly" if score >= THRESHOLD else "NO"
        print(f"  Threshold {THRESHOLD}? {flag}")

    return score


def main():
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    idx = build_index(raw)

    # Upcoming from matches table (what ESPN might show locally)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT match_date, home_team, away_team FROM matches ORDER BY match_date"
    )
    upcoming = cur.fetchall()
    conn.close()

    print("ALL fixtures in matches table with scores:")
    qualifiers = []
    for md, h, a in upcoming:
        # Map short DB names to app card names where needed
        home_app = h + (" Kangaroos" if h == "North Melbourne" else " Tigers" if h == "Richmond" else "")
        away_app = a + (" Kangaroos" if a == "North Melbourne" else " Tigers" if a == "Richmond" else "")
        # Use research names directly from DB for scoring
        score = explain(h, a, idx, verbose=False)
        if score is not None:
            mark = "YELLOW" if score >= THRESHOLD else "     "
            print(f"  {mark} {score:5.2f}  {md}  {h} vs {a}")
            if score >= THRESHOLD:
                qualifiers.append((score, md, h, a))

    print(f"\n{len(qualifiers)} games >= {THRESHOLD} in matches table")

    # Detailed breakdown for Richmond vs North Melbourne
    print("\n\nDETAILED: Richmond vs North Melbourne (Jun 21)")
    explain("Richmond Tigers", "North Melbourne Kangaroos", idx)

    # Also try home/away swapped as on card
    print("\nIf fixture listed as North Melbourne home:")
    explain("North Melbourne Kangaroos", "Richmond Tigers", idx)

    # Score ALL unique pairs to see top qualifiers (simulates full upcoming feed)
    print("\n\nTOP SCORING MATCHUPS (any date, static tables):")
    seen = set()
    all_scores = []
    for r in raw["matchup_ratings"]:
        a, b = r["matchup"].split(" vs ")
        pair = tuple(sorted([a, b]))
        if pair in seen:
            continue
        seen.add(pair)
        s = explain(a, b, idx, verbose=False)
        if s and s >= THRESHOLD:
            all_scores.append((s, a, b))
    all_scores.sort(reverse=True)
    for s, a, b in all_scores[:10]:
        print(f"  {s:.2f}  {a} vs {b}")


if __name__ == "__main__":
    main()
