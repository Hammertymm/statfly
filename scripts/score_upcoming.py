import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / "afl-flytime-v1.json"
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
    "Adelaide Crows": "Adelaide Crows",
    "Brisbane Lions": "Brisbane Lions",
    "Geelong Cats": "Geelong Cats",
    "Sydney Swans": "Sydney Swans",
    "West Coast Eagles": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
    "GWS GIANTS": "GWS GIANTS",
    "Gold Coast SUNS": "Gold Coast SUNS",
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


def afl_team(name):
    n = (name or "").lower()
    pairs = [
        ("north melbourne", "North Melbourne Kangaroos"),
        ("port adelaide", "Port Adelaide Power"),
        ("carlton", "Carlton Blues"),
        ("collingwood", "Collingwood Magpies"),
        ("essendon", "Essendon Bombers"),
        ("fremantle", "Fremantle Dockers"),
        ("gold coast", "Gold Coast Suns"),
        ("greater western", "Greater Western Sydney Giants"),
        ("gws", "Greater Western Sydney Giants"),
        ("hawthorn", "Hawthorn Hawks"),
        ("richmond", "Richmond Tigers"),
        ("st kilda", "St Kilda Saints"),
        ("st. kilda", "St Kilda Saints"),
        ("melbourne", "Melbourne Demons"),
        ("adelaide", "Adelaide Crows"),
        ("brisbane", "Brisbane Lions"),
        ("geelong", "Geelong Cats"),
        ("sydney", "Sydney Swans"),
        ("west coast", "West Coast Eagles"),
        ("western bulldog", "Western Bulldogs"),
    ]
    for k, v in pairs:
        if k in n:
            return v
    return name


def score_fixture(home_app, away_app, idx):
    home = AFL_RESEARCH_NAMES.get(home_app, home_app)
    away = AFL_RESEARCH_NAMES.get(away_app, away_app)
    close_rates, matchup_ratings, form_strength, margin_rating = idx
    key = f"{home}|{away}"
    cr = close_rates.get(key)
    mr = matchup_ratings.get(key)
    fh, fa = form_strength.get(home), form_strength.get(away)
    mh, ma = margin_rating.get(home), margin_rating.get(away)
    if None in (cr, mr, fh, fa, mh, ma):
        return None, None
    fb = 100 - abs(fh - fa)
    mb = 100 - abs(mh - ma)
    s = cr * 0.35 + fb * 0.25 + mb * 0.25 + mr * 0.15
    detail = {
        "close_rate": cr,
        "matchup_rating": mr,
        "form_home": fh,
        "form_away": fa,
        "margin_home": mh,
        "margin_away": ma,
        "form_balance": fb,
        "margin_balance": mb,
    }
    return s, detail


def main():
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    idx = build_index(raw)

    end = datetime.utcnow()
    start = end - timedelta(days=3)
    fwd = end + timedelta(days=21)
    fmt = lambda d: d.strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/australian-football/afl/scoreboard"
        f"?dates={fmt(start)}-{fmt(fwd)}"
    )
    data = json.loads(urllib.request.urlopen(url, timeout=20).read())

    upcoming = []
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        st = comp["status"]["type"]["state"]
        if st != "pre":
            continue
        cs = comp["competitors"]
        home = next(c for c in cs if c["homeAway"] == "home")
        away = next(c for c in cs if c["homeAway"] == "away")
        upcoming.append(
            {
                "date": ev["date"][:10],
                "home": afl_team(home["team"]["displayName"]),
                "away": afl_team(away["team"]["displayName"]),
            }
        )

    print(f"ESPN AFL upcoming fixtures: {len(upcoming)}\n")
    qualifiers = []
    for m in upcoming:
        s, d = score_fixture(m["home"], m["away"], idx)
        if s is None:
            print(f"  NO DATA  {m['date']}  {m['home']} vs {m['away']}")
            continue
        mark = "YELLOW" if s >= THRESHOLD else "      "
        print(f"  {mark} {s:5.2f}  {m['date']}  {m['home']} vs {m['away']}")
        if s >= THRESHOLD:
            qualifiers.append((s, m, d))

    print(f"\n{len(qualifiers)} yellow flies (>= {THRESHOLD})\n")

    for s, m, d in qualifiers:
        print("=" * 60)
        print(f"{m['home']} vs {m['away']}  ({m['date']})  score={s:.2f}")
        print(f"  close_rate x 0.35     = {d['close_rate']} -> {d['close_rate']*0.35:.3f}")
        print(f"  form_balance x 0.25   = {d['form_balance']} -> {d['form_balance']*0.25:.3f}")
        print(f"  margin_balance x 0.25 = {d['margin_balance']} -> {d['margin_balance']*0.25:.3f}")
        print(f"  matchup_rating x 0.15 = {d['matchup_rating']} -> {d['matchup_rating']*0.15:.3f}")


if __name__ == "__main__":
    main()
