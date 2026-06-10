import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / "nfl-flytime-v1.json"
THRESHOLD = 93


def build_index(raw):
    cr, mr, fs, mg = {}, {}, {}, {}
    for r in raw["form_strengths"]:
        fs[r["team"]] = r["strength"]
    for r in raw["team_margin_ratings"]:
        mg[r["team"]] = r["avg_margin"]
    for r in raw["matchup_ratings"]:
        a, b = r["matchup"].split(" vs ")
        mr[a + "|" + b] = mr[b + "|" + a] = r["avg_excitement"]
    for r in raw["matchup_close_rates"]:
        a, b = r["matchup"].split(" vs ")
        cr[a + "|" + b] = cr[b + "|" + a] = r["close_rate"]
    return cr, mr, fs, mg


def score(home, away, idx):
    cr, mr, fs, mg = idx
    key = home + "|" + away
    vals = [cr.get(key), mr.get(key), fs.get(home), fs.get(away), mg.get(home), mg.get(away)]
    if any(v is None for v in vals):
        return None
    fb = 100 - abs(fs[home] - fs[away])
    mb = 100 - abs(mg[home] - mg[away])
    return cr[key] * 0.35 + fb * 0.25 + mb * 0.25 + mr[key] * 0.15


def main():
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    idx = build_index(raw)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=3)
    fwd = end + timedelta(days=21)
    fmt = lambda d: d.strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        f"?dates={fmt(start)}-{fmt(fwd)}"
    )
    data = json.loads(urllib.request.urlopen(url, timeout=20).read())
    upcoming = []
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        if comp["status"]["type"]["state"] != "pre":
            continue
        cs = comp["competitors"]
        home = next(c for c in cs if c["homeAway"] == "home")
        away = next(c for c in cs if c["homeAway"] == "away")
        upcoming.append({
            "date": ev["date"][:10],
            "home": home["team"]["displayName"],
            "away": away["team"]["displayName"],
        })
    print(f"NFL upcoming: {len(upcoming)} (threshold {THRESHOLD})\n")
    q = 0
    for m in upcoming:
        s = score(m["home"], m["away"], idx)
        mark = "YELLOW" if s and s >= THRESHOLD else "      "
        if s and s >= THRESHOLD:
            q += 1
        print(f"  {mark} {s or 0:5.1f}  {m['date']}  {m['home']} vs {m['away']}")
    print(f"\n{q} yellow flies")


if __name__ == "__main__":
    main()
