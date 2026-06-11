"""
Build FlyTime v1 research tables from ESPN historical scoreboards.
Usage: python build_flytime_v1.py nba wnba ncaam mlb nhl ncaaf nrl
       python build_flytime_v1.py --all
"""
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent.parent

SEASON_WINDOWS = [
    ("2019", "20190901", "20200215"),
    ("2020", "20200901", "20210215"),
    ("2021", "20210901", "20220215"),
    ("2022", "20220901", "20230215"),
    ("2023", "20230901", "20240215"),
    ("2024", "20240901", "20250215"),
]

CFL_SEASON_WINDOWS = [
    ("2022", "20220601", "20221130"),
    ("2023", "20230601", "20231130"),
    ("2024", "20240601", "20241130"),
]

RUGBY_SEASON_WINDOWS = [
    ("2022-23", "20220801", "20230615"),
    ("2023-24", "20230801", "20240615"),
    ("2024-25", "20240801", "20250615"),
]

THRESHOLDS = [65, 68, 70, 72, 75, 78, 80, 85, 88, 90, 92, 93, 94, 95, 96, 97, 98]

NRL_SUBSTRINGS = [
    ("north queensland", "North Queensland Cowboys"),
    ("cowboy", "North Queensland Cowboys"),
    ("south sydney", "South Sydney Rabbitohs"),
    ("rabbitoh", "South Sydney Rabbitohs"),
    ("st george illawarra", "St George Illawarra Dragons"),
    ("dragon", "St George Illawarra Dragons"),
    ("new zealand", "New Zealand Warriors"),
    ("warrior", "New Zealand Warriors"),
    ("newcastle", "Newcastle Knights"),
    ("knight", "Newcastle Knights"),
    ("gold coast", "Gold Coast Titans"),
    ("titan", "Gold Coast Titans"),
    ("canberra", "Canberra Raiders"),
    ("raider", "Canberra Raiders"),
    ("parramatta", "Parramatta Eels"),
    ("eel", "Parramatta Eels"),
    ("penrith", "Penrith Panthers"),
    ("panther", "Penrith Panthers"),
    ("melbourne storm", "Melbourne Storm"),
    ("storm", "Melbourne Storm"),
    ("manly", "Manly Sea Eagles"),
    ("sea eagle", "Manly Sea Eagles"),
    ("canterbury", "Canterbury Bulldogs"),
    ("bulldog", "Canterbury Bulldogs"),
    ("cronulla", "Cronulla Sharks"),
    ("shark", "Cronulla Sharks"),
    ("sydney rooster", "Sydney Roosters"),
    ("rooster", "Sydney Roosters"),
    ("brisbane bronco", "Brisbane Broncos"),
    ("bronco", "Brisbane Broncos"),
    ("wests tiger", "Wests Tigers"),
    ("tiger", "Wests Tigers"),
    ("dolphin", "Dolphins"),
]

SPORT_CONFIG = {
    "nba": {
        "label": "NBA",
        "espn_sport": "basketball",
        "espn_league": "nba",
        "close_margin": 8,
        "chunk": 16,
    },
    "wnba": {
        "label": "WNBA",
        "espn_sport": "basketball",
        "espn_league": "wnba",
        "close_margin": 8,
        "chunk": 6,
    },
    "ncaam": {
        "label": "NCAAM",
        "espn_sport": "basketball",
        "espn_league": "mens-college-basketball",
        "close_margin": 8,
        "chunk": 50,
        "daily_fetch": True,
        "daily_ranges": [
            ("2022-23", "20221101", "20230415"),
            ("2023-24", "20231101", "20240415"),
            ("2024-25", "20241101", "20250415"),
        ],
    },
    "mlb": {
        "label": "MLB",
        "espn_sport": "baseball",
        "espn_league": "mlb",
        "close_margin": 2,
        "chunk": 16,
    },
    "nhl": {
        "label": "NHL",
        "espn_sport": "hockey",
        "espn_league": "nhl",
        "close_margin": 1,
        "chunk": 16,
    },
    "ncaaf": {
        "label": "NCAAF",
        "espn_sport": "football",
        "espn_league": "college-football",
        "close_margin": 8,
        "chunk": 50,
    },
    "nrl": {
        "label": "NRL",
        "espn_sport": "rugby-league",
        "espn_league": "3",
        "close_margin": 12,
        "chunk": 8,
        "normalize": "nrl",
    },
    "cfl": {
        "label": "CFL",
        "espn_sport": "football",
        "espn_league": "cfl",
        "close_margin": 8,
        "chunk": 4,
        "out_file": "cfl-flytime-v1.json",
        "season_windows": CFL_SEASON_WINDOWS,
    },
    "urc": {
        "label": "URC",
        "espn_sport": "rugby",
        "espn_league": "270557",
        "close_margin": 12,
        "chunk": 8,
        "out_file": "rugby-urc-flytime-v1.json",
        "season_windows": RUGBY_SEASON_WINDOWS,
    },
    "top14": {
        "label": "Top 14",
        "espn_sport": "rugby",
        "espn_league": "270559",
        "close_margin": 12,
        "chunk": 8,
        "out_file": "rugby-top14-flytime-v1.json",
        "season_windows": RUGBY_SEASON_WINDOWS,
    },
}


def nrl_normalize(name):
    n = (name or "").lower()
    for sub, canonical in NRL_SUBSTRINGS:
        if sub in n:
            return canonical
    return name


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


def parse_games_from_events(data, seen, norm, label, games):
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
        if norm == "nrl":
            ht, at = nrl_normalize(ht), nrl_normalize(at)
        if not ht or not at:
            continue
        margin = abs(hs - as_)
        games.append({
            "id": eid,
            "season": label,
            "date": ev.get("date") or comp.get("date") or "",
            "home": ht,
            "away": at,
            "home_score": hs,
            "away_score": as_,
            "margin": margin,
        })
        seen.add(eid)
        n += 1
    return n


def load_games_daily(cfg):
    games = []
    seen = set()
    sport, league = cfg["espn_sport"], cfg["espn_league"]
    norm = cfg.get("normalize")
    for label, start, end in cfg["daily_ranges"]:
        d0 = datetime.strptime(start, "%Y%m%d")
        d1 = datetime.strptime(end, "%Y%m%d")
        n = 0
        cur = d0
        while cur <= d1:
            ds = cur.strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={ds}"
            try:
                data = fetch_json(url)
                n += parse_games_from_events(data, seen, norm, label, games)
            except Exception:
                pass
            cur += timedelta(days=1)
            time.sleep(0.05)
        print(f"  {label}: {n} finals (daily fetch)", flush=True)
    games.sort(key=lambda g: g["date"])
    return games


def load_games(cfg):
    if cfg.get("daily_fetch"):
        return load_games_daily(cfg)
    games = []
    seen = set()
    sport, league = cfg["espn_sport"], cfg["espn_league"]
    norm = cfg.get("normalize")
    windows = cfg.get("season_windows") or SEASON_WINDOWS
    for label, start, end in windows:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={start}-{end}"
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"  skip {label}: {e}")
            continue
        n = parse_games_from_events(data, seen, norm, label, games)
        print(f"  {label}: {n} finals")
    games.sort(key=lambda g: g["date"])
    return games


def recent_team_games(games, team, close_margin, n=10):
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
                "close": g["margin"] <= close_margin,
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


def build_team_tables(games, close_margin):
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    form_strengths, margin_ratings = [], []
    for team in teams:
        recent = recent_team_games(games, team, close_margin)
        fs = form_strength(recent)
        am = avg_margin_rating(recent)
        if fs is not None:
            form_strengths.append({"team": team, "strength": fs})
        if am is not None:
            margin_ratings.append({"team": team, "avg_margin": am})
    return form_strengths, margin_ratings


def matchup_key(a, b):
    return f"{a} vs {b}"


def build_matchup_tables(games, close_margin):
    pairs = defaultdict(list)
    for g in games:
        pairs[tuple(sorted([g["home"], g["away"]]))].append(g)
    ratings, close_rates = [], []
    for (a, b), gs in pairs.items():
        margins = [x["margin"] for x in gs]
        close_n = sum(1 for m in margins if m <= close_margin)
        cr = 100.0 * close_n / len(margins)
        avg_m = mean(margins)
        tight = max(0, 1 - avg_m / (close_margin * 3))
        excitement = round(0.7 * cr + 0.3 * tight * 100, 2)
        mk = matchup_key(a, b)
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
        mk2 = matchup_key(b, a)
        ratings.append({**row, "matchup": mk2})
        close_rates.append({
            "matchup": mk2,
            "games": len(gs),
            "close_games": close_n,
            "close_rate": round(cr, 2),
        })
    return ratings, close_rates


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


def build_one(key):
    cfg = SPORT_CONFIG[key]
    out_path = ROOT / cfg.get("out_file", f"{key}-flytime-v1.json")
    close = cfg["close_margin"]
    print(f"\n=== {cfg['label']} ({key}) ===")
    print("Fetching finals from ESPN...")
    games = load_games(cfg)
    print(f"Total games: {len(games)}")
    if len(games) < 50:
        print("  WARNING: few games — output may be sparse")

    form_strengths, margin_ratings = build_team_tables(games, close)
    matchup_ratings, close_rates = build_matchup_tables(games, close)

    output = {
        "meta": {
            "sport": cfg["label"],
            "engine": "v1-bootstrap",
            "formula": "close*0.35 + form_balance*0.25 + margin_balance*0.25 + matchup*0.15",
            "close_margin": close,
            "games_sampled": len(games),
            "week_chunk": cfg["chunk"],
            "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "matchup_ratings": matchup_ratings,
        "matchup_close_rates": close_rates,
        "form_strengths": form_strengths,
        "team_margin_ratings": margin_ratings,
    }
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    thr = calibrate(output, cfg["chunk"]) if len(games) >= 20 else 85
    print(f"Wrote {out_path.name}: {len(form_strengths)} teams, threshold {thr}")
    return {"file": out_path.name, "threshold": thr, "tag": cfg.get("tag", key.upper()), "games": len(games)}


def main():
    keys = list(SPORT_CONFIG.keys()) if "--all" in sys.argv else [a for a in sys.argv[1:] if a in SPORT_CONFIG]
    if not keys:
        print("Usage: python build_flytime_v1.py nba wnba ... | --all")
        print("Keys:", ", ".join(SPORT_CONFIG))
        sys.exit(1)
    for key in keys:
        build_one(key)


if __name__ == "__main__":
    main()
