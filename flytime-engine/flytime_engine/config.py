"""League registry, thresholds, and ESPN feed configuration.

Mirrors FLY_V1_REGISTRY and ESPN_FEEDS from scorefly/index.html.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent  # scorefly/
FLYTIME_JSON_DIR = ROOT
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "flytime_engine.db"

AFL_FLY_Q4_ELAPSED_SEC = 20 * 60

FLY_BLOWOUT_MARGIN = {
    "basketball": 16,
    "football": 16,
    "hockey": 3,
    "baseball": 5,
    "australian-football": 24,
    "rugby-league": 24,
    "rugby": 24,
    "soccer": 3,
}

# Historical backfill windows per league key (sport|league)
DEFAULT_SEASON_WINDOWS = [
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

NBL_SEASON_WINDOWS = [
    ("2023-24", "20231001", "20240630"),
    ("2024-25", "20241001", "20250630"),
    ("2025-26", "20251001", "20260630"),
]

NCAAM_DAILY_RANGES = [
    ("2022-23", "20221101", "20230415"),
    ("2023-24", "20231101", "20240415"),
    ("2024-25", "20241101", "20250415"),
]

THRESHOLD_CANDIDATES = [65, 68, 70, 72, 75, 78, 80, 85, 88, 90, 92, 93, 94, 95, 96, 97, 98]
PERCENTILE_CANDIDATES = [0.10, 0.15, 0.20, 0.25, 0.30]

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


@dataclass(frozen=True)
class LeagueConfig:
    sport: str
    league_code: str
    label: str
    tag: Optional[str] = None
    flytime_file: Optional[str] = None
    threshold: Optional[float] = None
    close_margin: int = 8
    chunk_size: int = 16
    normalize: Optional[str] = None  # nrl | afl
    season_windows: Optional[tuple] = None
    daily_ranges: Optional[tuple] = None


# FLY_V1_REGISTRY + ESPN_FEEDS unified
LEAGUES: list[LeagueConfig] = [
    LeagueConfig("basketball", "nba", "NBA", "NBA", "nba-flytime-v1.json", 88, 8, 16),
    LeagueConfig("football", "nfl", "NFL", "NFL", "nfl-flytime-v1.json", 95, 8, 16),
    LeagueConfig("baseball", "mlb", "MLB", "MLB", "mlb-flytime-v1.json", 85, 2, 16),
    LeagueConfig("hockey", "nhl", "NHL", "NHL", "nhl-flytime-v1.json", 78, 1, 16),
    LeagueConfig("soccer", "usa.1", "MLS", "MLS", "soccer-usa-1-flytime-v1.json", 96, 1, 10),
    LeagueConfig("soccer", "eng.1", "EPL", "EPL", "soccer-eng-1-flytime-v1.json", 96, 1, 10),
    LeagueConfig("soccer", "esp.1", "La Liga", "LIGA", "soccer-esp-1-flytime-v1.json", 96, 1, 10),
    LeagueConfig("soccer", "uefa.champions", "UCL", "UCL", "soccer-uefa-champions-flytime-v1.json", 93, 1, 8),
    LeagueConfig("soccer", "uefa.europa", "UEL", "UEL", "soccer-uefa-europa-flytime-v1.json", 95, 1, 8),
    LeagueConfig("soccer", "ger.1", "Bundesliga", "BUN", "soccer-ger-1-flytime-v1.json", 92, 1, 9),
    LeagueConfig("soccer", "ita.1", "Serie A", "SER", "soccer-ita-1-flytime-v1.json", 95, 1, 10),
    LeagueConfig("soccer", "fra.1", "Ligue 1", "L1", "soccer-fra-1-flytime-v1.json", 95, 1, 9),
    LeagueConfig("soccer", "eng.2", "Championship", "CH", "soccer-eng-2-flytime-v1.json", 98, 1, 12),
    LeagueConfig("soccer", "ned.1", "Eredivisie", "ERE", "soccer-ned-1-flytime-v1.json", 88, 1, 9),
    LeagueConfig("soccer", "por.1", "Primeira Liga", "POR", "soccer-por-1-flytime-v1.json", 97, 1, 9),
    LeagueConfig("soccer", "sco.1", "Scottish Premiership", "SCO", "soccer-sco-1-flytime-v1.json", 85, 1, 6),
    LeagueConfig("soccer", "tur.1", "Super Lig", "TUR", "soccer-tur-1-flytime-v1.json", 95, 1, 9),
    LeagueConfig("soccer", "bra.1", "Brasileirao", "BRA", "soccer-bra-1-flytime-v1.json", 97, 1, 10),
    LeagueConfig("soccer", "arg.1", "Liga Profesional", "ARG", "soccer-arg-1-flytime-v1.json", 98, 1, 10),
    LeagueConfig("soccer", "mex.1", "Liga MX", "MX", "soccer-mex-1-flytime-v1.json", 90, 1, 9),
    LeagueConfig("soccer", "jpn.1", "J1 League", "J1", "soccer-jpn-1-flytime-v1.json", 96, 1, 10),
    LeagueConfig("soccer", "eng.3", "League One", "LO", "soccer-eng-3-flytime-v1.json", 97, 1, 12),
    LeagueConfig("soccer", "eng.4", "League Two", "LT", "soccer-eng-4-flytime-v1.json", 97, 1, 12),
    LeagueConfig("soccer", "chn.1", "Chinese Super League", "CSL", "soccer-chn-1-flytime-v1.json", 94, 1, 10),
    LeagueConfig("soccer", "bel.1", "Belgian Pro League", "BEL", "soccer-bel-1-flytime-v1.json", 88, 1, 8),
    LeagueConfig("soccer", "sui.1", "Swiss Super League", "SUI", "soccer-sui-1-flytime-v1.json", 85, 1, 8),
    LeagueConfig("soccer", "gre.1", "Greek Super League", "GRE", "soccer-gre-1-flytime-v1.json", 93, 1, 8),
    LeagueConfig("soccer", "ita.2", "Serie B", "SB", "soccer-ita-2-flytime-v1.json", 97, 1, 10),
    LeagueConfig("soccer", "ksa.1", "Saudi Pro League", "KSA", "soccer-ksa-1-flytime-v1.json", 96, 1, 9),
    LeagueConfig("soccer", "rus.1", "Russian Premier League", "RUS", "soccer-rus-1-flytime-v1.json", 94, 1, 8),
    LeagueConfig("soccer", "aus.1", "A-League", "ALE", "soccer-aus-1-flytime-v1.json", 85, 1, 6),
    LeagueConfig("soccer", "irl.1", "League of Ireland", "IRL", "soccer-irl-1-flytime-v1.json", 93, 1, 5),
    LeagueConfig("soccer", "ind.1", "ISL", "ISL", "soccer-ind-1-flytime-v1.json", 85, 1, 6),
    LeagueConfig("soccer", "rsa.1", "PSL", "PSL", "soccer-rsa-1-flytime-v1.json", 95, 1, 6),
    LeagueConfig("soccer", "conmebol.libertadores", "Libertadores", "LIB",
                 "soccer-conmebol-libertadores-flytime-v1.json", 96, 1, 8),
    LeagueConfig("soccer", "eng.w.1", "WSL", "WSL", "soccer-eng-w-1-flytime-v1.json", 78, 1, 6),
    LeagueConfig("australian-football", "afl", "AFL", "FT", "afl-flytime-v1.json", 75, 12, 16, normalize="afl"),
    LeagueConfig("cricket", "8044", "Big Bash League", None, None, None, 20, 8),
    LeagueConfig("cricket", "8048", "IPL", None, None, None, 20, 8),
    LeagueConfig("cricket", "23694", "Cricket", None, None, None, 20, 8),
    LeagueConfig("basketball", "wnba", "WNBA", "WNBA", "wnba-flytime-v1.json", 70, 8, 6),
    LeagueConfig("basketball", "nbl", "NBL", "NBL", "nbl-flytime-v1.json", 70, 8, 8,
                 season_windows=NBL_SEASON_WINDOWS),
    LeagueConfig("basketball", "mens-college-basketball", "NCAAM", "NCAAM",
                 "ncaam-flytime-v1.json", 97, 8, 50, daily_ranges=NCAAM_DAILY_RANGES),
    LeagueConfig("football", "college-football", "NCAAF", "NCAAF",
                 "ncaaf-flytime-v1.json", 96, 8, 50),
    LeagueConfig("football", "cfl", "CFL", "CFL", "cfl-flytime-v1.json", 70, 8, 4,
                 season_windows=CFL_SEASON_WINDOWS),
    LeagueConfig("rugby", "270557", "URC", "URC", "rugby-urc-flytime-v1.json", 90, 12, 8,
                 season_windows=RUGBY_SEASON_WINDOWS),
    LeagueConfig("rugby", "270559", "Top 14", "T14", "rugby-top14-flytime-v1.json", 88, 12, 8,
                 season_windows=RUGBY_SEASON_WINDOWS),
    LeagueConfig("rugby-league", "3", "NRL", "NRL", "nrl-flytime-v1.json", 85, 12, 8, normalize="nrl"),
]

FORMULA_VERSIONS = {
    "v1": {
        "name": "FlyTime v1 (production)",
        "weights": {"close_rate": 0.35, "form_balance": 0.25, "margin_balance": 0.25, "matchup": 0.15},
        "is_production": True,
    },
    "v2": {
        "name": "FlyTime v2 (close-heavy)",
        "weights": {"close_rate": 0.45, "form_balance": 0.20, "margin_balance": 0.20, "matchup": 0.15},
        "is_production": False,
    },
    "v3": {
        "name": "FlyTime v3 (form-heavy)",
        "weights": {"close_rate": 0.25, "form_balance": 0.35, "margin_balance": 0.25, "matchup": 0.15},
        "is_production": False,
    },
    "experimental": {
        "name": "Experimental (matchup-heavy)",
        "weights": {"close_rate": 0.25, "form_balance": 0.20, "margin_balance": 0.20, "matchup": 0.35},
        "is_production": False,
    },
}

# Polling intervals (seconds)
POLL_FAST_SEC = 12
POLL_FLYTIME_SEC = 8
POLL_IDLE_SEC = 60
POLL_FULL_SWEEP_EVERY = 15  # fast cycles before full resweep


def league_key(sport: str, league_code: str) -> str:
    return f"{sport}|{league_code}"


def get_league(sport: str, league_code: str) -> Optional[LeagueConfig]:
    for lg in LEAGUES:
        if lg.sport == sport and lg.league_code == league_code:
            return lg
    return None


def get_season_windows(league: LeagueConfig) -> list[tuple[str, str, str]]:
    if league.daily_ranges:
        return list(league.daily_ranges)
    if league.season_windows:
        return list(league.season_windows)
    return list(DEFAULT_SEASON_WINDOWS)
