"""ESPN API client and event parsing — mirrors index.html mapEspnEvent."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .config import AFL_RESEARCH_NAMES, NRL_SUBSTRINGS


def fetch_json(url: str, retries: int = 3) -> dict:
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ScoreFly-FlyTime-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(0.5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def scoreboard_url(sport: str, league: str, date_from: str, date_to: Optional[str] = None) -> str:
    dates = date_from if date_to is None else f"{date_from}-{date_to}"
    return f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={dates}"


def clock_to_sec(clock: str) -> int:
    if not clock:
        return 0
    parts = "".join(c if c.isdigit() or c == ":" else "" for c in str(clock)).split(":")
    if len(parts) == 2:
        return (int(parts[0]) or 0) * 60 + (int(parts[1]) or 0)
    return int(parts[0]) if parts and parts[0] else 0


def nrl_normalize(name: str) -> str:
    n = (name or "").lower()
    for sub, canonical in NRL_SUBSTRINGS:
        if sub in n:
            return canonical
    return name


def map_research_team(name: str, normalize: Optional[str]) -> str:
    if normalize == "afl":
        return AFL_RESEARCH_NAMES.get(name, name)
    if normalize == "nrl":
        return nrl_normalize(name)
    return name


def espn_status(comp: dict) -> str:
    t = (comp.get("status") or {}).get("type") or {}
    if t.get("state") == "in":
        return "live"
    if t.get("state") == "post" or t.get("completed"):
        return "finished"
    if t.get("state") == "pre":
        return "upcoming"
    name = t.get("name") or ""
    if name in ("STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD"):
        return "live"
    if name == "STATUS_FINAL":
        return "finished"
    event_time = comp.get("date") or ""
    try:
        if datetime.fromisoformat(event_time.replace("Z", "+00:00")) < datetime.now(timezone.utc):
            return "finished"
    except ValueError:
        pass
    return "upcoming"


def team_name(competitor: dict) -> str:
    team = competitor.get("team") or {}
    return team.get("displayName") or team.get("name") or ""


def team_id(competitor: dict) -> str:
    team = competitor.get("team") or {}
    if team.get("id"):
        return str(team["id"])
    uid = team.get("uid") or ""
    if "~t:" in uid:
        return uid.split("~t:")[1].split("~")[0]
    return str(competitor.get("id") or "")


def parse_score(competitor: dict, sport: str) -> Optional[int]:
    s = competitor.get("score")
    if sport == "cricket":
        s = str(s or "0").split(",")[0].strip()
    elif isinstance(s, dict):
        s = s.get("value", s.get("displayValue"))
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def cricket_chase_fields(comp: dict) -> dict:
    """Extract T20 chase fields when available."""
    situation = comp.get("situation") or {}
    return {
        "cricket_runs_req": situation.get("runsRemaining"),
        "cricket_overs_left": situation.get("oversRemaining"),
    }


@dataclass
class ParsedMatch:
    espn_event_id: str
    sport: str
    league_code: str
    home_team: str
    away_team: str
    home_team_id: str
    away_team_id: str
    status: str
    scheduled_at: str
    home_score: int = 0
    away_score: int = 0
    period: int = 0
    clock_raw: str = ""
    clock_sec: int = 0
    venue: str = ""
    season: str = ""
    cricket_runs_req: Optional[int] = None
    cricket_overs_left: Optional[float] = None
    raw_status_name: str = ""


def parse_event(event: dict, sport: str, league_code: str, normalize: Optional[str] = None) -> Optional[ParsedMatch]:
    comp = (event.get("competitions") or [None])[0]
    if not comp:
        return None
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

    hs = parse_score(home, sport)
    as_ = parse_score(away, sport)
    if hs is None:
        hs = 0
    if as_ is None:
        as_ = 0

    ht = map_research_team(team_name(home), normalize)
    at = map_research_team(team_name(away), normalize)
    if not ht or not at:
        return None

    status = espn_status(comp)
    venue_obj = comp.get("venue") or {}
    venue = venue_obj.get("fullName") or ""

    season = ""
    if event.get("season"):
        season = str(event["season"].get("year") or event["season"].get("displayName") or "")

    status_type = (comp.get("status") or {}).get("type") or {}
    clock_raw = (comp.get("status") or {}).get("displayClock") or ""
    period = (comp.get("status") or {}).get("period") or 0

    cricket_extra = cricket_chase_fields(comp) if sport == "cricket" else {}

    return ParsedMatch(
        espn_event_id=str(event.get("id")),
        sport=sport,
        league_code=league_code,
        home_team=ht,
        away_team=at,
        home_team_id=team_id(home),
        away_team_id=team_id(away),
        status=status,
        scheduled_at=event.get("date") or comp.get("date") or "",
        home_score=hs,
        away_score=as_,
        period=period,
        clock_raw=clock_raw,
        clock_sec=clock_to_sec(clock_raw),
        venue=venue,
        season=season,
        cricket_runs_req=cricket_extra.get("cricket_runs_req"),
        cricket_overs_left=cricket_extra.get("cricket_overs_left"),
        raw_status_name=status_type.get("name") or "",
    )


def fetch_scoreboard(
    sport: str,
    league: str,
    date_from: str,
    date_to: Optional[str] = None,
    normalize: Optional[str] = None,
) -> list[ParsedMatch]:
    url = scoreboard_url(sport, league, date_from, date_to)
    data = fetch_json(url)
    results = []
    for ev in data.get("events", []):
        parsed = parse_event(ev, sport, league, normalize)
        if parsed:
            results.append(parsed)
    return results


def fetch_live_window(
    sport: str,
    league: str,
    normalize: Optional[str] = None,
    days_back: int = 1,
    days_fwd: int = 1,
) -> list[ParsedMatch]:
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=days_back)).strftime("%Y%m%d")
    end = (today + timedelta(days=days_fwd)).strftime("%Y%m%d")
    return fetch_scoreboard(sport, league, start, end, normalize)


def fetch_daily(
    sport: str,
    league: str,
    start: str,
    end: str,
    normalize: Optional[str] = None,
    sleep_sec: float = 0.05,
) -> list[ParsedMatch]:
    """Fetch one day at a time for high-volume leagues (NCAAM)."""
    d0 = datetime.strptime(start, "%Y%m%d")
    d1 = datetime.strptime(end, "%Y%m%d")
    seen: set[str] = set()
    games: list[ParsedMatch] = []
    cur = d0
    while cur <= d1:
        ds = cur.strftime("%Y%m%d")
        for m in fetch_scoreboard(sport, league, ds, normalize=normalize):
            if m.espn_event_id not in seen:
                seen.add(m.espn_event_id)
                games.append(m)
        cur += timedelta(days=1)
        time.sleep(sleep_sec)
    return games
