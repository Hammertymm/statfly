"""
Build NFL FlyTime v1 research tables from ESPN historical scoreboards.
Mirrors AFL table shape for export to nfl-flytime-v1.json.
"""
import json
import sqlite3
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent.parent
OUT_JSON = ROOT / "nfl-flytime-v1.json"
DB_PATH = Path(__file__).parent / "data" / "scorefly.db"

# Same "close game" definition as live FlyTime / CLOSE_MARGIN.football in index.html
NFL_CLOSE_MARGIN = 8

# ESPN scoreboard windows (regular season + playoffs per year)
SEASON_WINDOWS = [
    ("2019", "20190901", "20200215"),
    ("2020", "20200901", "20210215"),
    ("2021", "20210901", "20220215"),
    ("2022", "20220901", "20230215"),
    ("2023", "20230901", "20240215"),
    ("2024", "20240901", "20250215"),
]


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read())


def team_name(competitor):
    return (competitor.get("team") or {}).get("displayName") or (competitor.get("team") or {}).get("name") or ""


def parse_score(competitor):
    s = competitor.get("score")
    if s is not None and isinstance(s, dict):
        s = s.get("value", s.get("displayValue"))
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def load_games():
    games = []
    seen = set()
    for label, start, end in SEASON_WINDOWS:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={start}-{end}"
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"  skip {label}: {e}")
            continue
        n = 0
        for ev in data.get("events", []):
            eid = ev.get("id")
            if eid in seen:
                continue
            comp = (ev.get("competitions") or [None])[0]
            if not comp:
                continue
            st = (comp.get("status") or {}).get("type") or {}
            if st.get("state") != "post" and not st.get("completed"):
                continue
            cs = comp.get("competitors") or []
            if len(cs) < 2:
                continue
            home = next((c for c in cs if c.get("homeAway") == "home"), cs[0])
            away = next((c for c in cs if c.get("homeAway") == "away"), cs[1])
            hs, as_ = parse_score(home), parse_score(away)
            if hs is None or as_ is None:
                continue
            ht, at = team_name(home), team_name(away)
            if not ht or not at:
                continue
            date = ev.get("date") or comp.get("date") or ""
            margin = abs(hs - as_)
            games.append({
                "id": eid,
                "season": label,
                "date": date,
                "home": ht,
                "away": at,
                "home_score": hs,
                "away_score": as_,
                "margin": margin,
            })
            seen.add(eid)
            n += 1
        print(f"  {label}: {n} finals")
    games.sort(key=lambda g: g["date"])
    return games


def recent_team_games(games, team, n=10):
    tg = []
    for g in reversed(games):
        if g["home"] == team or g["away"] == team:
            is_home = g["home"] == team
            ts = g["home_score"] if is_home else g["away_score"]
            os = g["away_score"] if is_home else g["home_score"]
            tg.append({
                "margin": abs(ts - os),
                "team_margin": ts - os,
                "win": ts > os,
                "close": g["margin"] <= NFL_CLOSE_MARGIN,
            })
            if len(tg) >= n:
                break
    return list(reversed(tg))


def form_strength(recent):
    if len(recent) < 3:
        return None
    num = den = 0
    for i, g in enumerate(recent[-5:]):
        wgt = i + 1
        num += (1.0 if g["win"] else 0.0) * wgt
        den += wgt
    win_score = num / den if den else 0.5
    close_rate = sum(1 for g in recent if g["close"]) / len(recent)
    # 0-100 scale aligned with AFL table range
    return round(40 + 40 * win_score + 20 * close_rate, 1)


def avg_margin_rating(recent):
    if len(recent) < 3:
        return None
    return round(mean(g["team_margin"] for g in recent), 1)


def build_team_tables(games):
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    form_strengths = []
    margin_ratings = []
    for team in teams:
        recent = recent_team_games(games, team)
        fs = form_strength(recent)
        am = avg_margin_rating(recent)
        if fs is not None:
            form_strengths.append({"team": team, "strength": fs})
        if am is not None:
            margin_ratings.append({"team": team, "avg_margin": am})
    return form_strengths, margin_ratings


def matchup_key(a, b):
    return f"{a} vs {b}"


def build_matchup_tables(games):
    pairs = defaultdict(list)
    for g in games:
        a, b = g["home"], g["away"]
        pairs[tuple(sorted([a, b]))].append(g)

    ratings = []
    close_rates = []
    for (a, b), gs in pairs.items():
        margins = [x["margin"] for x in gs]
        close_n = sum(1 for m in margins if m <= NFL_CLOSE_MARGIN)
        cr = 100.0 * close_n / len(margins)
        avg_m = mean(margins)
        tight = max(0, 1 - avg_m / (NFL_CLOSE_MARGIN * 3))
        excitement = round(0.7 * cr + 0.3 * tight * 100, 2)
        mk = matchup_key(a, b)
        ratings.append({
            "matchup": mk,
            "games_played": len(gs),
            "avg_margin": round(avg_m, 2),
            "avg_excitement": excitement,
        })
        close_rates.append({
            "matchup": mk,
            "games": len(gs),
            "close_games": close_n,
            "close_rate": round(cr, 2),
        })
        # reverse key for lookup symmetry in export
        mk2 = matchup_key(b, a)
        ratings.append({
            "matchup": mk2,
            "games_played": len(gs),
            "avg_margin": round(avg_m, 2),
            "avg_excitement": excitement,
        })
        close_rates.append({
            "matchup": mk2,
            "games": len(gs),
            "close_games": close_n,
            "close_rate": round(cr, 2),
        })
    return ratings, close_rates


def save_sqlite(games, output):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS nfl_historical_matches (
            event_id TEXT, season TEXT, match_date TEXT,
            home_team TEXT, away_team TEXT,
            home_score INT, away_score INT, margin INT
        );
        CREATE TABLE IF NOT EXISTS nfl_matchup_ratings (
            matchup TEXT, games_played INT, avg_margin REAL, avg_excitement REAL
        );
        CREATE TABLE IF NOT EXISTS nfl_matchup_close_rates (
            matchup TEXT, games INT, close_games INT, close_rate REAL
        );
        CREATE TABLE IF NOT EXISTS nfl_form_strengths (
            team TEXT, strength REAL
        );
        CREATE TABLE IF NOT EXISTS nfl_team_margin_ratings (
            team TEXT, avg_margin REAL
        );
    """)
    c.execute("DELETE FROM nfl_historical_matches")
    for g in games:
        c.execute(
            "INSERT INTO nfl_historical_matches VALUES (?,?,?,?,?,?,?,?)",
            (g["id"], g["season"], g["date"], g["home"], g["away"], g["home_score"], g["away_score"], g["margin"]),
        )
    for table, rows, cols in [
        ("nfl_matchup_ratings", output["matchup_ratings"], ("matchup", "games_played", "avg_margin", "avg_excitement")),
        ("nfl_matchup_close_rates", output["matchup_close_rates"], ("matchup", "games", "close_games", "close_rate")),
        ("nfl_form_strengths", output["form_strengths"], ("team", "strength")),
        ("nfl_team_margin_ratings", output["team_margin_ratings"], ("team", "avg_margin")),
    ]:
        c.execute(f"DELETE FROM {table}")
        ph = ",".join("?" * len(cols))
        for row in rows:
            c.execute(f"INSERT INTO {table} VALUES ({ph})", tuple(row[c] for c in cols))
    conn.commit()
    conn.close()


def main():
    print("Fetching NFL finals from ESPN...")
    games = load_games()
    print(f"Total NFL games: {len(games)}")
    if len(games) < 100:
        raise SystemExit("Too few games fetched — aborting")

    form_strengths, margin_ratings = build_team_tables(games)
    matchup_ratings, close_rates = build_matchup_tables(games)

    output = {
        "meta": {
            "sport": "NFL",
            "engine": "v1-bootstrap",
            "formula": "close*0.35 + form_balance*0.25 + margin_balance*0.25 + matchup*0.15",
            "close_margin": NFL_CLOSE_MARGIN,
            "games_sampled": len(games),
            "built": datetime.utcnow().strftime("%Y-%m-%d"),
        },
        "matchup_ratings": matchup_ratings,
        "matchup_close_rates": close_rates,
        "form_strengths": form_strengths,
        "team_margin_ratings": margin_ratings,
    }

    OUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
    save_sqlite(games, output)
    print(f"Wrote {OUT_JSON}")
    print(f"  teams: {len(form_strengths)}")
    print(f"  matchup rows: {len(matchup_ratings)}")


if __name__ == "__main__":
    main()
