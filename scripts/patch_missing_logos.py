#!/usr/bin/env python3
"""Patch fixable missing logos + correct BBL ID mapping."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
GALLERY = ROOT / "logo-gallery.html"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_team_halo_config import (  # noqa: E402
    HALO_STRENGTH,
    analyze_logo,
    build_espn_lookup,
    match_espn_team,
    norm_name,
    pick_logo_url,
    render_gallery,
    upgrade_logo_url,
)

USER_AGENT = "ScoreFly-LogoPatch/1.0"

# Verified via ESPN page titles (IDs do NOT match URL slugs).
BBL_LOGOS: dict[str, tuple[str, str]] = {
    "Adelaide Strikers": ("509667", "https://a.espncdn.com/i/teamlogos/cricket/500/509667.png"),
    "Brisbane Heat": ("509668", "https://a.espncdn.com/i/teamlogos/cricket/500/509668.png"),
    "Hobart Hurricanes": ("509669", "https://a.espncdn.com/i/teamlogos/cricket/500/509669.png"),
    "Melbourne Renegades": ("509671", "https://a.espncdn.com/i/teamlogos/cricket/500/509671.png"),
    "Melbourne Stars": ("509672", "https://a.espncdn.com/i/teamlogos/cricket/500/509672.png"),
    "Perth Scorchers": ("509670", "https://a.espncdn.com/i/teamlogos/cricket/500/509670.png"),
    "Sydney Sixers": ("509673", "https://a.espncdn.com/i/teamlogos/cricket/500/509673.png"),
    "Sydney Thunder": ("509674", "https://a.espncdn.com/i/teamlogos/cricket/500/509674.png"),
}

SIX_NATIONS_CODES = {
    "England": "eng",
    "France": "fra",
    "Ireland": "irl",
    "Italy": "ita",
    "Scotland": "sco",
    "Wales": "wal",
}

# Extra ESPN team pools for relegated / renamed clubs.
EXTRA_ESPN_LEAGUES = [
    ("soccer", "ger.2"),   # 2. Bundesliga
    ("soccer", "esp.2"),   # La Liga 2
    ("soccer", "fra.2"),   # Ligue 2
    ("soccer", "ned.2"),
    ("soccer", "eng.2"),   # Championship (also covers some L1/L2 edges)
    ("soccer", "por.2"),
    ("soccer", "sco.2"),
    ("soccer", "tur.1"),
    ("soccer", "chn.1"),
    ("soccer", "ksa.1"),
    ("soccer", "gre.1"),
    ("soccer", "sui.1"),
    ("soccer", "ita.2"),
    ("soccer", "jpn.1"),
    ("soccer", "mex.1"),
    ("soccer", "ind.1"),
    ("soccer", "rsa.1"),
    ("soccer", "irl.1"),
    ("soccer", "eng.w.1"),
    ("rugby", "270559"),   # Top 14
]

NAME_ALIASES: dict[str, str] = {
    norm_name("FC Köln"): norm_name("1. FC Köln"),
    norm_name("1. FC Köln"): norm_name("FC Cologne"),
    norm_name("Wolverhampton Wanderers"): norm_name("Wolves"),
    norm_name("Brighton"): norm_name("Brighton & Hove Albion"),
    norm_name("İstanbul Başakşehir"): norm_name("Istanbul Basaksehir"),
    norm_name("Başakşehir"): norm_name("Istanbul Basaksehir"),
    norm_name("Mazatlán"): norm_name("Mazatlan FC"),
    norm_name("Famalicão"): norm_name("Famalicao"),
    norm_name("Hellas Verona"): norm_name("Verona"),
    norm_name("Tottenham Women"): norm_name("Tottenham Hotspur"),
    norm_name("RKC Waalwijk"): norm_name("RKC Waalwijk"),
    norm_name("Waalwijk"): norm_name("RKC Waalwijk"),
    norm_name("FeralpiSalo"): norm_name("FeralpiSalò"),
    norm_name("Cape Town City"): norm_name("Cape Town City FC"),
    norm_name("Hyderabad FC"): norm_name("Hyderabad"),
    norm_name("UCD"): norm_name("University College Dublin"),
    norm_name("Yverdon"): norm_name("Yverdon Sport"),
    norm_name("Bayonne"): norm_name("Aviron Bayonnais"),
    norm_name("Reims"): norm_name("Stade de Reims"),
    norm_name("Kasımpaşa"): norm_name("Kasimpasa"),
    norm_name("Mazatlán"): norm_name("Mazatlan FC"),
    norm_name("Hellas Verona"): norm_name("Verona"),
    norm_name("Vizela"): norm_name("Vitoria Guimaraes"),
    norm_name("1. FC Köln"): norm_name("FC Cologne"),
}

# Direct crest overrides when ESPN has no logo field or cricket IDs are offline.
MANUAL_LOGO_BY_FAVKEY: dict[str, tuple[str, str]] = {
    "Tottenham Women|Women's Super League": (
        "20062",
        "https://a.espncdn.com/i/teamlogos/soccer/500/20062.png",
    ),
    "Kasımpaşa|Süper Lig": (
        "6870",
        "https://a.espncdn.com/i/teamlogos/soccer/500/6870.png",
    ),
    "FC Köln|Bundesliga": (
        "122",
        "https://a.espncdn.com/i/teamlogos/soccer/500/122.png",
    ),
}


def fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return json.loads(res.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def load_espn_teams(sport: str, league: str) -> list[dict]:
    data = fetch_json(
        f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=500"
    )
    if not data:
        return []
    out = []
    for sport_obj in data.get("sports", []):
        for lg in sport_obj.get("leagues", []):
            for item in lg.get("teams", []):
                t = item.get("team") or {}
                if t:
                    out.append(t)
    return out


def match_with_aliases(name: str, lookup: dict[str, list[dict]]) -> dict | None:
    n = norm_name(name)
    keys = [n, NAME_ALIASES.get(n, n)]
    for key in keys:
        if key in lookup:
            return lookup[key][0]
    return match_espn_team(name, lookup)


def apply_visual(entry: dict, logo_url: str, espn_id: str = "") -> None:
    visual = analyze_logo(logo_url, None, None)
    entry["logoUrl"] = upgrade_logo_url(logo_url)
    entry["espnIds"] = [espn_id] if espn_id else []
    entry["haloColor"] = visual["haloColor"]
    entry["haloStrength"] = HALO_STRENGTH
    entry["dominantColor"] = visual["dominantColor"]
    entry["secondaryColor"] = visual["secondaryColor"]
    entry["needsContrastLift"] = visual["needsContrastLift"]
    entry["logoScale"] = visual["logoScale"]


def apply_from_espn(entry: dict, team: dict) -> bool:
    logo = pick_logo_url(team.get("logos")) or team.get("logo") or ""
    if not logo:
        return False
    apply_visual(entry, logo, str(team.get("id") or ""))
    return True


def build_global_lookup() -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = defaultdict(list)
    for sport, league in EXTRA_ESPN_LEAGUES:
        for team in load_espn_teams(sport, league):
            for alias, cands in build_espn_lookup([team]).items():
                if alias:
                    lookup[alias].extend(cands)
    return lookup


def probe_cricket_id(tid: int) -> str | None:
    url = f"https://www.espn.com/cricket/team/_/id/{tid}/x"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        m = re.search(r"<title>([^<]+)</title>", html)
        if not m:
            return None
        return m.group(1).split("Cricket")[0].strip()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def find_ipl_ids() -> dict[str, tuple[str, str]]:
    want = {
        "Chennai Super Kings",
        "Kolkata Knight Riders",
        "Mumbai Indians",
        "Sunrisers Hyderabad",
        "Delhi Capitals",
        "Rajasthan Royals",
        "Punjab Kings",
        "Royal Challengers Bengaluru",
        "Gujarat Titans",
        "Lucknow Super Giants",
    }
    found: dict[str, tuple[str, str]] = {}
    for tid in range(509600, 510200):
        crest = f"https://a.espncdn.com/i/teamlogos/cricket/500/{tid}.png"
        try:
            urllib.request.urlopen(crest, timeout=4)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
        title = probe_cricket_id(tid)
        if not title:
            continue
        for name in list(want):
            if norm_name(name) == norm_name(title) or norm_name(name) in norm_name(title):
                found[name] = (str(tid), crest)
                want.discard(name)
        if not want:
            break
    return found


def find_psl_ids() -> dict[str, tuple[str, str]]:
    want = {
        "Islamabad United",
        "Karachi Kings",
        "Lahore Qalandars",
        "Multan Sultans",
        "Peshawar Zalmi",
        "Quetta Gladiators",
    }
    found: dict[str, tuple[str, str]] = {}
    for tid in range(509600, 510200):
        crest = f"https://a.espncdn.com/i/teamlogos/cricket/500/{tid}.png"
        try:
            urllib.request.urlopen(crest, timeout=4)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
        title = probe_cricket_id(tid)
        if not title:
            continue
        for name in list(want):
            if norm_name(name) == norm_name(title):
                found[name] = (str(tid), crest)
                want.discard(name)
    return found


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    teams = data["teams"]
    global_lookup = build_global_lookup()

    # ESPN CDN only hosts BBL cricket crests (509667–509674); full ID scan is slow/noisy.
    ipl_ids: dict[str, tuple[str, str]] = {}
    psl_ids: dict[str, tuple[str, str]] = {}
    if "--scan-cricket" in sys.argv:
        print("Scanning IPL / PSL cricket IDs…")
        ipl_ids = find_ipl_ids()
        psl_ids = find_psl_ids()
        print(f"  IPL found: {len(ipl_ids)}  PSL found: {len(psl_ids)}")

    fixed_bbl = fixed_six = fixed_global = fixed_manual = fixed_ipl = fixed_psl = 0
    still_missing: list[dict] = []

    for entry in teams:
        league = entry.get("league", "")
        name = (entry.get("names") or [""])[0]

        # Always refresh BBL with verified IDs.
        if league == "Big Bash League" and name in BBL_LOGOS:
            espn_id, url = BBL_LOGOS[name]
            apply_visual(entry, url, espn_id)
            fixed_bbl += 1
            continue

        fav = entry.get("favKey", "")
        if fav in MANUAL_LOGO_BY_FAVKEY:
            espn_id, url = MANUAL_LOGO_BY_FAVKEY[fav]
            apply_visual(entry, url, espn_id)
            fixed_manual += 1
            continue

        if entry.get("logoUrl"):
            continue

        if league == "Six Nations Rugby" and name in SIX_NATIONS_CODES:
            code = SIX_NATIONS_CODES[name]
            apply_visual(entry, f"https://a.espncdn.com/i/teamlogos/countries/500/{code}.png")
            fixed_six += 1
            continue

        if league == "Indian Premier League" and name in ipl_ids:
            espn_id, url = ipl_ids[name]
            apply_visual(entry, url, espn_id)
            fixed_ipl += 1
            continue

        if league == "Pakistan Super League" and name in psl_ids:
            espn_id, url = psl_ids[name]
            apply_visual(entry, url, espn_id)
            fixed_psl += 1
            continue

        hit = match_with_aliases(name, global_lookup)
        if hit and apply_from_espn(entry, hit):
            fixed_global += 1
            continue

        still_missing.append(entry)

    data["teams"] = teams
    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    gallery_entries = []
    for t in teams:
        e = dict(t)
        e["logoMissing"] = not e.get("logoUrl")
        gallery_entries.append(e)
    GALLERY.write_text(render_gallery(gallery_entries), encoding="utf-8")

    print(f"BBL refreshed: {fixed_bbl}")
    print(f"Six Nations fixed: {fixed_six}")
    print(f"IPL fixed: {fixed_ipl}")
    print(f"PSL fixed: {fixed_psl}")
    print(f"Manual overrides fixed: {fixed_manual}")
    print(f"Global/secondary league fixed: {fixed_global}")
    print(f"Still missing: {len(still_missing)}")
    report = ROOT / "scripts" / "missing-logos.txt"
    if still_missing:
        by: dict[str, list[str]] = defaultdict(list)
        for t in still_missing:
            by[t["league"]].append(t["names"][0])
        lines = [f"Still missing: {len(still_missing)}", ""]
        for lg in sorted(by):
            lines.append(f"{lg} ({len(by[lg])})")
            for n in sorted(by[lg]):
                lines.append(f"  - {n}")
            lines.append("")
        report.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report: {report}")


if __name__ == "__main__":
    main()
