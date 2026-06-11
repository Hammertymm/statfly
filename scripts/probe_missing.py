#!/usr/bin/env python3
import json
import re
import unicodedata
import urllib.request

def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def load(sport: str, league: str) -> list[dict]:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=500"
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        out = []
        for sp in data.get("sports", []):
            for lg in sp.get("leagues", []):
                for item in lg.get("teams", []):
                    out.append(item["team"])
        return out
    except Exception as exc:
        print(f"LOAD FAIL {sport}/{league}: {exc}")
        return []


QUERIES = {
    "FC Köln": ("soccer", "ger.1"),
    "Hellas Verona": ("soccer", "ita.1"),
    "Salernitana": ("soccer", "ita.2"),
    "Changchun Yatai": ("soccer", "chn.1"),
    "Meizhou Hakka": ("soccer", "chn.1"),
    "Lamia": ("soccer", "gre.1"),
    "Hyderabad FC": ("soccer", "ind.1"),
    "Morecambe": ("soccer", "eng.4"),
    "UCD": ("soccer", "irl.1"),
    "Mazatlán": ("soccer", "mex.1"),
    "Cape Town City": ("soccer", "rsa.1"),
    "Boavista": ("soccer", "por.1"),
    "Chaves": ("soccer", "por.2"),
    "Vizela": ("soccer", "por.2"),
    "Abha": ("soccer", "ksa.1"),
    "Al Raed": ("soccer", "ksa.1"),
    "Yverdon": ("soccer", "sui.1"),
    "Bayonne": ("rugby", "270559"),
    "Albirex Niigata": ("soccer", "jpn.1"),
    "Consadole Sapporo": ("soccer", "jpn.1"),
    "Sagan Tosu": ("soccer", "jpn.1"),
    "Shonan Bellmare": ("soccer", "jpn.1"),
    "Yokohama FC": ("soccer", "jpn.1"),
    "Ascoli": ("soccer", "ita.2"),
    "Brescia": ("soccer", "ita.2"),
    "Pisa": ("soccer", "ita.2"),
    "Adana Demirspor": ("soccer", "tur.1"),
    "Hatayspor": ("soccer", "tur.1"),
}

cache: dict[str, list[dict]] = {}
for sport, league in set(QUERIES.values()):
    cache[f"{sport}|{league}"] = load(sport, league)

for want, (sport, league) in sorted(QUERIES.items()):
    w = norm(want)
    hit = None
    for team in cache[f"{sport}|{league}"]:
        names = [
            team.get("displayName", ""),
            team.get("name", ""),
            team.get("shortDisplayName", ""),
        ]
        for name in names:
            nn = norm(name)
            if nn == w or w in nn or nn in w:
                hit = team
                break
        if hit:
            break
    if hit:
        logo = hit.get("logo") or ""
        if not logo and hit.get("logos"):
            logo = hit["logos"][0].get("href", "")
        tag = "LOGO" if logo else "NO"
        print(f"{want:22} {hit['displayName']:28} id={hit['id']:6} {tag}")
        if logo:
            print(f"  {logo}")
    else:
        print(f"{want:22} NOT IN {league}")
