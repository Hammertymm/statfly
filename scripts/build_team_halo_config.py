#!/usr/bin/env python3
"""Build team-halo-config.json + logo-gallery.html for all ScoreFly teams."""
from __future__ import annotations

import io
import json
import re
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow required: pip install Pillow")

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
OUT_CONFIG = ROOT / "team-halo-config.json"
OUT_GALLERY = ROOT / "logo-gallery.html"

HALO_STRENGTH = 0.25
USER_AGENT = "ScoreFly-HaloBuilder/1.0"


def read_index() -> str:
    return INDEX.read_text(encoding="utf-8")


def extract_block(text: str, name: str) -> str:
    m = re.search(rf"const {name}\s*=\s*\{{([\s\S]*?)\n\}};", text)
    if m:
        return m.group(1)
    # Arrays (e.g. ESPN_FEEDS)
    m = re.search(rf"const {name}\s*=\s*\[([\s\S]*?)\n\];", text)
    return m.group(1) if m else ""


def parse_teams(text: str) -> dict[str, list[str]]:
    block = extract_block(text, "TEAMS")
    out: dict[str, list[str]] = {}
    for m in re.finditer(
        r"(?:'((?:\\'|[^'])*)'|\"([^\"]+)\"):\s*\[([^\]]+)\]",
        block,
    ):
        league = (m.group(1) or m.group(2) or "").replace("\\'", "'")
        names = re.findall(r"'((?:\\'|[^'])*)'", m.group(3))
        out[league] = [n.replace("\\'", "'") for n in names]
    return out


def parse_league_names(text: str) -> list[str]:
    block = extract_block(text, "LEAGUES")
    names = re.findall(r"n:'((?:\\'|[^'])*)'", block)
    return [n.replace("\\'", "'") for n in names]


def parse_espn_feeds(text: str) -> list[dict[str, str]]:
    block = extract_block(text, "ESPN_FEEDS")
    feeds = []
    for m in re.finditer(
        r"\{\s*sport:'([^']+)',\s*league:'([^']+)',\s*label:'([^']+)',\s*emoji:'[^']*'\s*\}",
        block,
    ):
        feeds.append({"sport": m.group(1), "league": m.group(2), "label": m.group(3)})
    if not feeds:
        # Fallback: read from full file if block extraction failed
        for m in re.finditer(
            r"\{\s*sport:'([^']+)',\s*league:'([^']+)',\s*label:'([^']+)',\s*emoji:'[^']*'\s*\}",
            text,
        ):
            feeds.append({"sport": m.group(1), "league": m.group(2), "label": m.group(3)})
    return feeds


def parse_feed_league_name(text: str) -> dict[str, str]:
    block = extract_block(text, "FEED_LEAGUE_NAME")
    out: dict[str, str] = {}
    for m in re.finditer(r"'([^']+)':'([^']+)'", block):
        out[m.group(1)] = m.group(2)
    for m in re.finditer(r"'([^']+)':\"([^\"]+)\"", block):
        out[m.group(1)] = m.group(2)
    return out


def slugify(*parts: str) -> str:
    raw = "-".join(parts).lower()
    raw = unicodedata.normalize("NFD", raw)
    raw = "".join(c for c in raw if unicodedata.category(c) != "Mn")
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "team"


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return json.loads(res.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_bytes(url: str) -> bytes | None:
    if not url:
        return None
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def pick_logo_url(logos: list[dict] | None) -> str:
    if not logos:
        return ""
    for rel in (["full", "default"], ["full", "primary_logo_on_black_color"], ["full", "scoreboard"]):
        for item in logos:
            if item.get("rel") == rel:
                return item.get("href", "")
    return logos[0].get("href", "")


def upgrade_logo_url(url: str) -> str:
    if not url:
        return url
    url = re.sub(r"teamlogos/([^/]+)/500-dark/", r"teamlogos/\1/500/", url)
    url = re.sub(r"teamlogos/([^/]+)/\d+/", r"teamlogos/\1/500/", url)
    return url


def hex_color(val: str | None) -> str | None:
    if not val:
        return None
    val = val.strip().lstrip("#")
    if len(val) == 6 and re.fullmatch(r"[0-9a-fA-F]{6}", val):
        return f"#{val.upper()}"
    return None


def saturation(r: int, g: int, b: int) -> float:
    mx, mn = max(r, g, b) / 255.0, min(r, g, b) / 255.0
    if mx == 0:
        return 0.0
    return (mx - mn) / mx


def brightness(r: int, g: int, b: int) -> float:
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def analyze_image(data: bytes) -> dict[str, Any]:
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    w, h = img.size
    thumb = img.resize((64, 64), Image.Resampling.LANCZOS)
    px = thumb.load()

    # Bounding box for logoScale
    xs, ys = [], []
    buckets: Counter[tuple[int, int, int]] = Counter()
    bright_sum, bright_n = 0.0, 0

    for y in range(64):
        for x in range(64):
            r, g, b, a = px[x, y]
            if a < 40:
                continue
            xs.append(x)
            ys.append(y)
            br = brightness(r, g, b)
            bright_sum += br
            bright_n += 1
            if br > 0.92 or br < 0.10:
                continue
            if saturation(r, g, b) < 0.12:
                continue
            rq, gq, bq = r // 16, g // 16, b // 16
            buckets[(rq, gq, bq)] += 1

    fill_ratio = 1.0
    if xs and ys and w and h:
        bw = (max(xs) - min(xs) + 1) / 64.0
        bh = (max(ys) - min(ys) + 1) / 64.0
        fill_ratio = max(bw, bh)

    logo_scale = round(min(1.25, max(0.85, 1.0 / max(fill_ratio, 0.55))), 2)

    dominant = None
    secondary = None
    if buckets:
        top = buckets.most_common(4)
        dominant = "#{:02X}{:02X}{:02X}".format(*(c * 16 + 8 for c in top[0][0]))
        if len(top) > 1:
            secondary = "#{:02X}{:02X}{:02X}".format(*(c * 16 + 8 for c in top[1][0]))

    avg_bright = bright_sum / bright_n if bright_n else 1.0
    return {
        "haloColor": dominant,
        "secondaryColor": secondary,
        "needsContrastLift": avg_bright < 0.32,
        "logoScale": logo_scale,
        "avgBrightness": round(avg_bright, 3),
    }


# Extra ESPN paths for leagues not in ESPN_FEEDS or without /teams endpoint
LEAGUE_ESPN_EXTRA: dict[str, tuple[str, str]] = {
    "Copa do Brasil": ("soccer", "bra.2"),
    "Big Bash League": ("cricket", "8044"),
    "Indian Premier League": ("cricket", "8048"),
    "ICC Cricket (ODI)": ("cricket", "23748"),
    "ICC Cricket (T20)": ("cricket", "23748"),
    "Six Nations Rugby": ("rugby", "180011"),
    "SA T20 Cricket": ("cricket", "8044"),
    "Pakistan Super League": ("cricket", "8046"),
    "Super Rugby Pacific": ("rugby", "242041"),
}


def espn_teams_url(sport: str, league: str) -> str:
    return f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=500"


def espn_scoreboard_url(sport: str, league: str, dates: str) -> str:
    return f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={dates}"


def load_espn_teams(sport: str, league: str) -> list[dict[str, Any]]:
    data = fetch_json(espn_teams_url(sport, league))
    if not data:
        return []
    teams = []
    for sport_obj in data.get("sports", []):
        for lg in sport_obj.get("leagues", []):
            for item in lg.get("teams", []):
                t = item.get("team") or {}
                teams.append(t)
    return teams


def load_espn_scoreboard_teams(sport: str, league: str) -> list[dict[str, Any]]:
    teams_by_id: dict[str, dict] = {}
    for dates in ("20240101-20241231", "20230101-20231231", "20250101-20251231"):
        data = fetch_json(espn_scoreboard_url(sport, league, dates))
        if not data:
            continue
        for ev in data.get("events", []):
            for comp in ev.get("competitions", []):
                for c in comp.get("competitors", []):
                    t = c.get("team") or {}
                    tid = str(t.get("id") or "")
                    if tid and tid not in teams_by_id:
                        teams_by_id[tid] = t
    return list(teams_by_id.values())


def espn_aliases(team: dict[str, Any]) -> set[str]:
    names = set()
    for key in ("displayName", "name", "shortDisplayName", "abbreviation", "nickname"):
        v = team.get(key)
        if v:
            names.add(norm_name(v))
    loc = team.get("location") or ""
    nick = team.get("nickname") or team.get("name") or ""
    if loc and nick:
        names.add(norm_name(f"{loc} {nick}"))
    return names


def build_espn_lookup(teams: list[dict[str, Any]]) -> dict[str, dict]:
    lookup: dict[str, list[dict]] = defaultdict(list)
    for t in teams:
        for alias in espn_aliases(t):
            lookup[alias].append(t)
    return lookup


def match_espn_team(name: str, lookup: dict[str, list[dict]]) -> dict | None:
    n = norm_name(name)
    alias = NAME_ALIASES.get(n, n)
    for key in (n, alias):
        if key in lookup:
            return lookup[key][0]
    # substring match (longer names first)
    best = None
    best_len = 0
    for alias_key, cands in lookup.items():
        if not alias_key or len(alias_key) < 4:
            continue
        if alias_key in n or n in alias_key or alias_key in alias or alias in alias_key:
            if len(alias_key) > best_len:
                best_len = len(alias_key)
                best = cands[0]
    return best


# Verified via ESPN page titles — IDs do not match URL slugs.
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

ICC_COUNTRY_CODES: dict[str, str] = {
    "Afghanistan": "afg",
    "Australia": "aus",
    "Bangladesh": "ban",
    "England": "eng",
    "India": "ind",
    "Ireland": "irl",
    "New Zealand": "nzl",
    "Pakistan": "pak",
    "South Africa": "rsa",
    "Sri Lanka": "sri",
    "West Indies": "wi",
    "Zimbabwe": "zim",
}

MANUAL_OVERRIDES: dict[str, dict[str, str]] = {
    "Collingwood Magpies|AFL": {
        "logoUrl": "https://a.espncdn.com/i/teamlogos/afl/500/coll.png",
        "haloColor": "#000000",
    },
}

# Leagues where ESPN id collisions make global lookup unsafe.
GLOBAL_LOOKUP_SKIP = {"Big Bash League", "ICC Cricket (ODI)", "ICC Cricket (T20)"}


def manual_logo_for(league: str, name: str) -> dict[str, str] | None:
    fav = f"{name}|{league}"
    if fav in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[fav]
    if league == "Big Bash League" and name in BBL_LOGOS:
        espn_id, url = BBL_LOGOS[name]
        return {"logoUrl": url, "espnId": espn_id}
    if league.startswith("ICC Cricket") and name in ICC_COUNTRY_CODES:
        code = ICC_COUNTRY_CODES[name]
        return {"logoUrl": f"https://a.espncdn.com/i/teamlogos/countries/500/{code}.png"}
    return None


def league_espn_path(
    league: str,
    feed_map: dict[str, str],
    feeds: list[dict[str, str]],
) -> tuple[str, str] | None:
    if league in LEAGUE_ESPN_EXTRA:
        return LEAGUE_ESPN_EXTRA[league]
    target = norm_name(league)
    for code, full in feed_map.items():
        if norm_name(full) == target:
            for f in feeds:
                if f["league"] == code:
                    return f["sport"], f["league"]
    return None


# ScoreFly roster name -> ESPN displayName aliases (when normalization is not enough)
NAME_ALIASES: dict[str, str] = {
    norm_name("Wolverhampton Wanderers"): norm_name("Wolves"),
    norm_name("Brighton"): norm_name("Brighton & Hove Albion"),
    norm_name("Leicester City"): norm_name("Leicester City"),
    norm_name("Luton Town"): norm_name("Luton Town"),
    norm_name("Sheffield United"): norm_name("Sheffield United"),
    norm_name("Nottingham Forest"): norm_name("Nottingham Forest"),
    norm_name("İstanbul Başakşehir"): norm_name("Istanbul Basaksehir"),
    norm_name("Başakşehir"): norm_name("Istanbul Basaksehir"),
    norm_name("Athletic Club"): norm_name("Athletic Club"),
    norm_name("Mazatlán"): norm_name("Mazatlan FC"),
    norm_name("Famalicão"): norm_name("Famalicao"),
    norm_name("St. Louis City SC"): norm_name("St. Louis CITY SC"),
    norm_name("D.C. United"): norm_name("D.C. United"),
    norm_name("Greater Western Sydney Giants"): norm_name("GWS Giants"),
    norm_name("North Melbourne Kangaroos"): norm_name("North Melbourne"),
    norm_name("St Kilda Saints"): norm_name("St Kilda"),
    norm_name("West Coast Eagles"): norm_name("West Coast"),
    norm_name("Port Adelaide Power"): norm_name("Port Adelaide"),
    norm_name("Gold Coast Suns"): norm_name("Gold Coast"),
    norm_name("Fremantle Dockers"): norm_name("Fremantle"),
    norm_name("Western Bulldogs"): norm_name("Western Bulldogs"),
    norm_name("North Queensland Cowboys"): norm_name("North Queensland"),
    norm_name("St George Illawarra Dragons"): norm_name("St. George Illawarra"),
    norm_name("New Zealand Warriors"): norm_name("Warriors"),
    norm_name("Canterbury Bulldogs"): norm_name("Bulldogs"),
    norm_name("Manly Sea Eagles"): norm_name("Manly-Warringah"),
    norm_name("Cronulla Sharks"): norm_name("Cronulla-Sutherland"),
    norm_name("Pumas UNAM"): norm_name("UNAM"),
    norm_name("Vélez Sársfield"): norm_name("Velez Sarsfield"),
    norm_name("Grêmio"): norm_name("Gremio"),
    norm_name("São Paulo"): norm_name("Sao Paulo"),
    norm_name("Cuiabá"): norm_name("Cuiaba"),
    norm_name("Goiás"): norm_name("Goias"),
    norm_name("Ceará"): norm_name("Ceara"),
}


def analyze_logo(url: str, espn_color: str | None, espn_alt: str | None) -> dict[str, Any]:
    data = fetch_bytes(upgrade_logo_url(url))
    if data:
        meta = analyze_image(data)
    else:
        meta = {
            "haloColor": None,
            "secondaryColor": None,
            "needsContrastLift": False,
            "logoScale": 1.0,
            "avgBrightness": 1.0,
        }
    halo = meta.get("haloColor") or hex_color(espn_color) or hex_color(espn_alt) or "#06F03C"
    secondary = meta.get("secondaryColor") or hex_color(espn_alt) or hex_color(espn_color) or halo
    return {
        "haloColor": halo,
        "secondaryColor": secondary,
        "dominantColor": halo,
        "needsContrastLift": bool(meta.get("needsContrastLift")),
        "logoScale": meta.get("logoScale", 1.0),
        "avgBrightness": meta.get("avgBrightness", 1.0),
        "logoOk": bool(data),
    }


def build_entry(
    league: str,
    name: str,
    espn: dict | None,
    override: dict | None,
) -> dict[str, Any]:
    fav_key = f"{name}|{league}"
    manual = manual_logo_for(league, name)
    if manual:
        override = {**(override or {}), **manual}
    logo = (override or {}).get("logoUrl", "")
    espn_id = (override or {}).get("espnId", "")
    espn_color = espn_alt = None
    if espn:
        espn_id = espn_id or str(espn.get("id") or "")
        logo = logo or pick_logo_url(espn.get("logos")) or espn.get("logo") or ""
        espn_color = espn.get("color")
        espn_alt = espn.get("alternateColor")
    logo = upgrade_logo_url(logo)
    visual = analyze_logo(logo, espn_color, espn_alt)
    if override:
        if override.get("haloColor"):
            visual["haloColor"] = override["haloColor"]
            visual["dominantColor"] = override["haloColor"]

    entry = {
        "teamId": slugify(name, league),
        "favKey": fav_key,
        "names": [name],
        "league": league,
        "espnIds": [espn_id] if espn_id else [],
        "logoUrl": logo,
        "haloColor": visual["haloColor"],
        "haloStrength": HALO_STRENGTH,
        "needsContrastLift": visual["needsContrastLift"],
        "dominantColor": visual["dominantColor"],
        "secondaryColor": visual["secondaryColor"],
        "logoScale": visual["logoScale"],
    }
    if not visual.get("logoOk"):
        entry["logoMissing"] = True
    return entry


def render_gallery(teams: list[dict[str, Any]]) -> str:
    data_json = json.dumps(teams, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ScoreFly Logo Gallery — {len(teams)} teams</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Inter,system-ui,sans-serif;background:#000;color:#fff;padding:16px 16px 80px}}
  h1{{font-size:20px;margin-bottom:4px}}
  .sub{{color:rgba(255,255,255,.55);font-size:13px;margin-bottom:16px;line-height:1.5}}
  .toolbar{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px;position:sticky;top:0;background:rgba(0,0,0,.92);padding:10px 0;z-index:10;backdrop-filter:blur(12px)}}
  .toolbar input,.toolbar select{{background:#111;border:1px solid rgba(255,255,255,.15);color:#fff;border-radius:8px;padding:8px 10px;font:inherit;font-size:13px}}
  .toolbar input{{flex:1;min-width:180px}}
  .stats{{font-size:12px;color:rgba(255,255,255,.5)}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:10px}}
  .card{{background:#080808;border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:10px}}
  .card.missing{{border-color:rgba(255,69,58,.45)}}
  .preview{{height:72px;display:flex;align-items:center;justify-content:center;margin-bottom:8px}}
  .team-logo-halo{{
    position:relative;display:flex;align-items:center;justify-content:center;
    width:32px;height:32px;padding:3px;--logo-scale:1;
  }}
  .team-logo-halo::before{{
    content:'';position:absolute;inset:0;border-radius:50%;pointer-events:none;z-index:0;
    background:radial-gradient(circle,rgba(255,255,255,0.06) 0%,rgba(255,255,255,0.02) 55%,transparent 72%);
  }}
  .team-logo-halo[data-contrast-lift]::before{{
    background:radial-gradient(circle,rgba(255,255,255,0.16) 0%,rgba(255,255,255,0.06) 55%,transparent 72%);
  }}
  .team-logo-halo img{{
    position:relative;z-index:1;width:100%;height:100%;object-fit:contain;
    transform:scale(var(--logo-scale));
    filter:brightness(1.06) saturate(1.14)
      drop-shadow(0 0 10px rgba(var(--halo-r),var(--halo-g),var(--halo-b),calc(var(--halo-strength)*0.9)))
      drop-shadow(0 0 4px rgba(255,255,255,0.12));
  }}
  .name{{font-size:11px;font-weight:600;line-height:1.25;margin-bottom:2px}}
  .league{{font-size:10px;color:rgba(255,255,255,.45);margin-bottom:6px}}
  .meta{{font-size:9px;color:rgba(255,255,255,.35);line-height:1.45;word-break:break-all}}
  .meta input{{width:100%;background:#111;border:1px solid rgba(255,255,255,.12);color:#fff;border-radius:4px;padding:2px 4px;font-size:9px;margin-top:2px}}
  .export{{position:fixed;bottom:0;left:0;right:0;padding:12px 16px;background:rgba(0,0,0,.95);border-top:1px solid rgba(255,255,255,.1);display:flex;gap:10px;justify-content:center}}
  .export button{{background:#06f03c;color:#000;border:none;border-radius:10px;padding:12px 20px;font-weight:700;font:inherit;cursor:pointer}}
</style>
</head>
<body>
<h1>ScoreFly Logo Gallery</h1>
<p class="sub">{len(teams)} teams — halo V2 preview (32px, strength 0.25). Edit <code>logoScale</code> / <code>haloColor</code> / <code>haloStrength</code> inline, then export JSON for <code>team-halo-config.json</code>.</p>
<div class="toolbar">
  <input id="q" type="search" placeholder="Filter team or league…" oninput="render()">
  <select id="leagueFilter" onchange="render()"><option value="">All leagues</option></select>
  <label class="stats"><input type="checkbox" id="missingOnly" onchange="render()"> Missing logos only</label>
  <span class="stats" id="count"></span>
</div>
<div class="grid" id="grid"></div>
<div class="export">
  <button type="button" onclick="exportConfig()">Export adjusted team-halo-config.json</button>
</div>
<script>
const TEAMS = {data_json};
const leagues = [...new Set(TEAMS.map(t => t.league))].sort();
const sel = document.getElementById('leagueFilter');
leagues.forEach(l => {{ const o = document.createElement('option'); o.value = l; o.textContent = l; sel.appendChild(o); }});

function hexRgb(hex) {{
  const h = (hex||'').replace('#','');
  if (h.length !== 6) return [6,240,60];
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
}}

function cardHtml(t, i) {{
  const [r,g,b] = hexRgb(t.haloColor);
  const lift = t.needsContrastLift ? ' data-contrast-lift' : '';
  const scale = t.logoScale != null && t.logoScale !== 1 ? ';--logo-scale:'+t.logoScale : '';
  const style = '--halo-r:'+r+';--halo-g:'+g+';--halo-b:'+b+';--halo-strength:'+(t.haloStrength||0.25)+scale;
  const img = t.logoUrl
    ? '<img src="'+t.logoUrl+'" alt="" onerror="this.style.opacity=0.2">'
    : '<span style="opacity:.3;font-size:10px">no img</span>';
  return '<div class="card'+(t.logoMissing?' missing':'')+'" data-i="'+i+'">'+
    '<div class="preview"><div class="team-logo-halo" style="'+style+'"'+lift+'>'+img+'</div></div>'+
    '<div class="name">'+t.names[0]+'</div><div class="league">'+t.league+'</div>'+
    '<div class="meta">favKey: '+t.favKey+'<br>'+
    'halo <input data-k="haloColor" data-i="'+i+'" value="'+t.haloColor+'" onchange="patch('+i+',this)">'+
    'scale <input data-k="logoScale" data-i="'+i+'" type="number" step="0.01" min="0.85" max="1.25" value="'+(t.logoScale||1)+'" onchange="patch('+i+',this)">'+
    'str <input data-k="haloStrength" data-i="'+i+'" type="number" step="0.01" min="0" max="0.35" value="'+(t.haloStrength||0.25)+'" onchange="patch('+i+',this)">'+
    'lift <input data-k="needsContrastLift" data-i="'+i+'" type="checkbox" '+(t.needsContrastLift?'checked':'')+' onchange="patch('+i+',this)">'+
    '</div></div>';
}}

function patch(i, el) {{
  const k = el.dataset.k;
  let v = el.type === 'checkbox' ? el.checked : el.value;
  if (k === 'logoScale' || k === 'haloStrength') v = parseFloat(v);
  TEAMS[i][k] = v;
  render();
}}

function render() {{
  const q = document.getElementById('q').value.toLowerCase();
  const lf = document.getElementById('leagueFilter').value;
  const miss = document.getElementById('missingOnly').checked;
  const filtered = TEAMS.map((t,i) => ({{t,i}})).filter(({{t}}) => {{
    if (lf && t.league !== lf) return false;
    if (miss && !t.logoMissing) return false;
    if (q && !(t.names[0]+' '+t.league+' '+t.favKey).toLowerCase().includes(q)) return false;
    return true;
  }});
  document.getElementById('grid').innerHTML = filtered.map(({{t,i}}) => cardHtml(t,i)).join('');
  document.getElementById('count').textContent = filtered.length + ' shown';
}}

function exportConfig() {{
  const out = {{ version: '2.0', defaultHaloStrength: 0.25, teams: TEAMS.map(t => {{
    const e = {{ ...t }};
    delete e.logoMissing;
    delete e.avgBrightness;
    return e;
  }})}};
  const blob = new Blob([JSON.stringify(out, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'team-halo-config.json';
  a.click();
}}

render();
</script>
</body>
</html>
"""


def main() -> None:
    text = read_index()
    teams_by_league = parse_teams(text)
    league_names = parse_league_names(text)
    feeds = parse_espn_feeds(text)
    feed_map = parse_feed_league_name(text)

    league_cache: dict[str, list[dict]] = {}
    pending: list[tuple[str, str, dict | None, dict | None]] = []

    for league in league_names:
        team_names = teams_by_league.get(league, [])
        if not team_names:
            continue

        path = league_espn_path(league, feed_map, feeds)
        espn_teams: list[dict] = []
        if path:
            key = f"{path[0]}|{path[1]}"
            if key not in league_cache:
                print(f"Fetching ESPN teams: {league} ({path[0]}/{path[1]})")
                espn_teams = load_espn_teams(*path)
                if len(espn_teams) < max(3, len(team_names) // 4):
                    sb = load_espn_scoreboard_teams(*path)
                    if sb:
                        espn_teams = sb
                league_cache[key] = espn_teams
                print(f"  -> {len(espn_teams)} ESPN teams")
            else:
                espn_teams = league_cache[key]

        lookup = build_espn_lookup(espn_teams)

        for name in team_names:
            fav_key = f"{name}|{league}"
            pending.append((league, name, match_espn_team(name, lookup) if lookup else None, MANUAL_OVERRIDES.get(fav_key)))

    # Global ESPN lookup across all leagues (helps UCL/UEL/domestic mismatches).
    global_lookup: dict[str, list[dict]] = defaultdict(list)
    for espn_teams in league_cache.values():
        for alias, cands in build_espn_lookup(espn_teams).items():
            if alias:
                global_lookup[alias].extend(cands)

    resolved_pending: list[tuple[str, str, dict | None, dict | None]] = []
    for league, name, espn, override in pending:
        manual = manual_logo_for(league, name)
        if manual:
            override = {**(override or {}), **manual}
            espn = None
        elif not espn and league not in GLOBAL_LOOKUP_SKIP:
            espn = match_espn_team(name, global_lookup)
        resolved_pending.append((league, name, espn, override))

    print(f"Analyzing {len(resolved_pending)} logos (parallel)…")
    entries: list[dict[str, Any]] = []
    missing_logos = 0

    def work(item: tuple[str, str, dict | None, dict | None]) -> dict[str, Any]:
        league, name, espn, override = item
        return build_entry(league, name, espn, override)

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(work, item): item for item in resolved_pending}
        done = 0
        for fut in as_completed(futures):
            entry = fut.result()
            entries.append(entry)
            done += 1
            if entry.get("logoMissing"):
                missing_logos += 1
            if done % 50 == 0 or done == len(resolved_pending):
                print(f"  {done}/{len(resolved_pending)} analyzed, {missing_logos} missing")

    entries.sort(key=lambda e: (e["league"], e["names"][0]))

    config = {
        "version": "2.0",
        "defaultHaloStrength": HALO_STRENGTH,
        "teams": [{k: v for k, v in e.items() if k not in ("logoMissing", "avgBrightness")} for e in entries],
    }
    OUT_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_GALLERY.write_text(render_gallery(entries), encoding="utf-8")

    print(f"\nWrote {len(entries)} teams to {OUT_CONFIG}")
    print(f"Missing logos: {missing_logos}")
    print(f"Gallery: {OUT_GALLERY}")


if __name__ == "__main__":
    main()
