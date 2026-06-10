"""
Build FlyTime v1 bootstrap tables for all soccer leagues in the app.
Usage: python build_soccer_flytime.py [league-slug ...]
       python build_soccer_flytime.py --all
Writes soccer-{slug}-flytime-v1.json and soccer-thresholds.json
"""
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent.parent

SOCCER_SEASON_WINDOWS = [
    ("2019-20", "20190801", "20200715"),
    ("2020-21", "20200901", "20210615"),
    ("2021-22", "20210801", "20220615"),
    ("2022-23", "20220801", "20230615"),
    ("2023-24", "20230801", "20240615"),
    ("2024-25", "20240801", "20250615"),
]

# (espn league key, label, tag, games per matchday chunk for calibration)
SOCCER_LEAGUES = [
    ("usa.1", "MLS", "MLS", 10),
    ("eng.1", "EPL", "EPL", 10),
    ("esp.1", "La Liga", "LIGA", 10),
    ("ger.1", "Bundesliga", "BUN", 9),
    ("ita.1", "Serie A", "SER", 10),
    ("fra.1", "Ligue 1", "L1", 9),
    ("eng.2", "Championship", "CH", 12),
    ("ned.1", "Eredivisie", "ERE", 9),
    ("por.1", "Primeira Liga", "POR", 9),
    ("sco.1", "Scottish Prem", "SCO", 6),
    ("tur.1", "Super Lig", "TUR", 9),
    ("bra.1", "Brasileirao", "BRA", 10),
    ("arg.1", "Liga Profesional", "ARG", 10),
    ("mex.1", "Liga MX", "MX", 9),
    ("aus.1", "A-League", "ALE", 6),
    ("irl.1", "League of Ireland", "IRL", 5),
    ("ind.1", "ISL", "ISL", 6),
    ("rsa.1", "PSL", "PSL", 6),
    ("eng.w.1", "WSL", "WSL", 6),
    ("uefa.champions", "UCL", "UCL", 8),
    ("uefa.europa", "UEL", "UEL", 8),
    ("conmebol.libertadores", "Libertadores", "LIB", 8),
]

THRESHOLDS = [65, 68, 70, 72, 75, 78, 80, 85, 88, 90, 92, 93, 94, 95, 96, 97, 98]
CLOSE_MARGIN = 1


def league_slug(league_key):
    return league_key.replace(".", "-")


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read())


def team_name(competitor):
    team = competitor.get("team") or {}
    return team.get("displayName") or team.get("name") or ""


def parse_score(competitor):
    s = competitor.get("score")
    if s is not None and isinstance(s, dict):
        s = s.get("value", s.get("displayValue"))
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def load_games(league_key):
    games = []
    seen = set()
    for label, start, end in SOCCER_SEASON_WINDOWS:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_key}/scoreboard?dates={start}-{end}"
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"  skip {label}: {e}", flush=True)
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
            games.append({
                "id": eid,
                "season": label,
                "date": ev.get("date") or comp.get("date") or "",
                "home": ht,
                "away": at,
                "home_score": hs,
                "away_score": as_,
                "margin": abs(hs - as_),
            })
            seen.add(eid)
            n += 1
        print(f"  {label}: {n} finals", flush=True)
        time.sleep(0.1)
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
                "close": g["margin"] <= CLOSE_MARGIN,
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
    return round(40 + 40 * win_score + 20 * close_rate, 1)


def avg_margin_rating(recent):
    if len(recent) < 3:
        return None
    return round(mean(g["team_margin"] for g in recent), 1)


def build_tables(games):
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    form_strengths, margin_ratings = [], []
    for team in teams:
        recent = recent_team_games(games, team)
        fs = form_strength(recent)
        am = avg_margin_rating(recent)
        if fs is not None:
            form_strengths.append({"team": team, "strength": fs})
        if am is not None:
            margin_ratings.append({"team": team, "avg_margin": am})

    pairs = defaultdict(list)
    for g in games:
        pairs[tuple(sorted([g["home"], g["away"]]))].append(g)
    ratings, close_rates = [], []
    for (a, b), gs in pairs.items():
        margins = [x["margin"] for x in gs]
        close_n = sum(1 for m in margins if m <= CLOSE_MARGIN)
        cr = 100.0 * close_n / len(margins)
        avg_m = mean(margins)
        tight = max(0, 1 - avg_m / (CLOSE_MARGIN * 3))
        excitement = round(0.7 * cr + 0.3 * tight * 100, 2)
        mk = f"{a} vs {b}"
        row = {
            "matchup": mk,
            "games_played": len(gs),
            "avg_margin": round(avg_m, 2),
            "avg_excitement": excitement,
        }
        ratings.append(row)
        close_rates.append({
            "matchup": mk,
            "games": len(gs),
            "close_games": close_n,
            "close_rate": round(cr, 2),
        })
        mk2 = f"{b} vs {a}"
        ratings.append({**row, "matchup": mk2})
        close_rates.append({
            "matchup": mk2,
            "games": len(gs),
            "close_games": close_n,
            "close_rate": round(cr, 2),
        })
    return form_strengths, margin_ratings, ratings, close_rates


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


def score_match(home, away, idx):
    cr, mr, fs, mg = idx
    key = f"{home}|{away}"
    vals = [cr.get(key), mr.get(key), fs.get(home), fs.get(away), mg.get(home), mg.get(away)]
    if any(v is None for v in vals):
        return None
    fb = 100 - abs(fs[home] - fs[away])
    mb = 100 - abs(mg[home] - mg[away])
    return cr[key] * 0.35 + fb * 0.25 + mb * 0.25 + mr[key] * 0.15


def calibrate(raw, chunk):
    idx = build_index(raw)
    pairs = set()
    gp_map = {}
    for r in raw["matchup_close_rates"]:
        a, b = r["matchup"].split(" vs ")
        pairs.add((a, b))
        gp_map[f"{a}|{b}"] = max(gp_map.get(f"{a}|{b}", 0), r["games"])
    by_gp = []
    for h, a in pairs:
        s = score_match(h, a, idx)
        if s is None:
            continue
        for _ in range(min(gp_map.get(f"{h}|{a}", 1), 4)):
            by_gp.append(s)
    if not by_gp:
        return 85
    weeks = [by_gp[i : i + chunk] for i in range(0, len(by_gp), chunk)]
    weeks = [w for w in weeks if w]
    best = (85, 999.0)
    for thr in THRESHOLDS:
        counts = [sum(1 for s in wk if s >= thr) for wk in weeks]
        avg = mean(counts)
        if abs(avg - 2) < abs(best[1] - 2):
            best = (thr, avg)
    return best[0]


def build_league(league_key, label, tag, chunk):
    slug = league_slug(league_key)
    out_name = f"soccer-{slug}-flytime-v1.json"
    print(f"\n=== {label} ({league_key}) ===", flush=True)
    games = load_games(league_key)
    print(f"Total: {len(games)}", flush=True)
    if len(games) < 20:
        print("  WARNING: sparse data", flush=True)
    fs, mg, ratings, close_rates = build_tables(games)
    output = {
        "meta": {
            "sport": label,
            "league": league_key,
            "engine": "v1-bootstrap",
            "formula": "close*0.35 + form_balance*0.25 + margin_balance*0.25 + matchup*0.15",
            "close_margin": CLOSE_MARGIN,
            "games_sampled": len(games),
            "week_chunk": chunk,
            "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "matchup_ratings": ratings,
        "matchup_close_rates": close_rates,
        "form_strengths": fs,
        "team_margin_ratings": mg,
    }
    (ROOT / out_name).write_text(json.dumps(output, indent=2), encoding="utf-8")
    thr = calibrate(output, chunk) if len(games) >= 20 else 85
    print(f"Wrote {out_name}: {len(fs)} teams, threshold {thr}", flush=True)
    return {
        "league_key": league_key,
        "slug": slug,
        "file": out_name,
        "tag": tag,
        "threshold": thr,
        "games": len(games),
        "teams": len(fs),
    }


def main():
    by_slug = {league_slug(k): (k, label, tag, chunk) for k, label, tag, chunk in SOCCER_LEAGUES}
    if "--all" in sys.argv:
        targets = list(by_slug.keys())
    else:
        targets = [a for a in sys.argv[1:] if a in by_slug]
    if not targets:
        print("Usage: python build_soccer_flytime.py --all | soccer-eng-1 ...")
        print("Slugs:", ", ".join(sorted(by_slug)))
        sys.exit(1)
    results = []
    for slug in targets:
        league_key, label, tag, chunk = by_slug[slug]
        results.append(build_league(league_key, label, tag, chunk))
    thresh_path = ROOT / "soccer-thresholds.json"
    thresh_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {thresh_path.name}", flush=True)


if __name__ == "__main__":
    main()
