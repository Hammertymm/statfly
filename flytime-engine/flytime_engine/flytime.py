"""FlyTime scoring, live detection, and formula versions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import (
    AFL_FLY_Q4_ELAPSED_SEC,
    FLYTIME_JSON_DIR,
    FORMULA_VERSIONS,
    LeagueConfig,
)
from .espn import ParsedMatch


@dataclass
class FlyTimeIndex:
    close_rates: dict[str, float]
    matchup_ratings: dict[str, float]
    form_strength: dict[str, float]
    margin_rating: dict[str, float]
    chunk_size: int = 16
    close_margin: int = 8


@dataclass
class FlyTimeResult:
    score: Optional[float]
    is_yellow: bool
    threshold: float
    formula_version: str
    components: dict[str, float]


class FlyTimeEngine:
    """Loads v1 JSON tables and scores matchups across formula versions."""

    def __init__(self, json_dir: Path = FLYTIME_JSON_DIR):
        self.json_dir = json_dir
        self._tables: dict[str, FlyTimeIndex] = {}

    def load_league(self, league: LeagueConfig) -> Optional[FlyTimeIndex]:
        if not league.flytime_file:
            return None
        key = f"{league.sport}|{league.league_code}"
        if key in self._tables:
            return self._tables[key]
        path = self.json_dir / league.flytime_file
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        idx = self._build_index(raw)
        self._tables[key] = idx
        return idx

    def load_all(self, leagues: list[LeagueConfig]) -> int:
        loaded = 0
        for lg in leagues:
            if self.load_league(lg):
                loaded += 1
        return loaded

    @staticmethod
    def _build_index(raw: dict) -> FlyTimeIndex:
        close_rates: dict[str, float] = {}
        matchup_ratings: dict[str, float] = {}
        form_strength: dict[str, float] = {}
        margin_rating: dict[str, float] = {}

        for r in raw.get("form_strengths", []):
            form_strength[r["team"]] = r["strength"]
        for r in raw.get("team_margin_ratings", []):
            margin_rating[r["team"]] = r["avg_margin"]
        for r in raw.get("matchup_ratings", []):
            parts = (r.get("matchup") or "").split(" vs ")
            if len(parts) == 2:
                k = f"{parts[0]}|{parts[1]}"
                matchup_ratings[k] = r["avg_excitement"]
                matchup_ratings[f"{parts[1]}|{parts[0]}"] = r["avg_excitement"]
        for r in raw.get("matchup_close_rates", []):
            parts = (r.get("matchup") or "").split(" vs ")
            if len(parts) == 2:
                k = f"{parts[0]}|{parts[1]}"
                close_rates[k] = r["close_rate"]
                close_rates[f"{parts[1]}|{parts[0]}"] = r["close_rate"]

        meta = raw.get("meta") or {}
        return FlyTimeIndex(
            close_rates=close_rates,
            matchup_ratings=matchup_ratings,
            form_strength=form_strength,
            margin_rating=margin_rating,
            chunk_size=meta.get("week_chunk", 16),
            close_margin=meta.get("close_margin", 8),
        )

    def score_matchup(
        self,
        home: str,
        away: str,
        idx: FlyTimeIndex,
        threshold: float,
        formula_version: str = "v1",
    ) -> FlyTimeResult:
        weights = FORMULA_VERSIONS.get(formula_version, FORMULA_VERSIONS["v1"])["weights"]
        key = f"{home}|{away}"
        cr = idx.close_rates.get(key)
        mr = idx.matchup_ratings.get(key)
        fh = idx.form_strength.get(home)
        fa = idx.form_strength.get(away)
        mh = idx.margin_rating.get(home)
        ma = idx.margin_rating.get(away)

        if any(v is None for v in (cr, mr, fh, fa, mh, ma)):
            return FlyTimeResult(None, False, threshold, formula_version, {})

        form_balance = 100 - abs(fh - fa)
        margin_balance = 100 - abs(mh - ma)
        components = {
            "close_rate": cr,
            "form_balance": form_balance,
            "margin_balance": margin_balance,
            "matchup": mr,
        }
        total = sum(components[k] * weights[k] for k in weights)
        return FlyTimeResult(
            score=round(total, 2),
            is_yellow=total >= threshold,
            threshold=threshold,
            formula_version=formula_version,
            components=components,
        )

    def score_for_league(
        self,
        match: ParsedMatch,
        league: LeagueConfig,
        formula_version: str = "v1",
    ) -> FlyTimeResult:
        threshold = league.threshold or 85.0
        idx = self.load_league(league)
        if not idx:
            return FlyTimeResult(None, False, threshold, formula_version, {})
        return self.score_matchup(
            match.home_team, match.away_team, idx, threshold, formula_version
        )


def is_flytime_live(match: ParsedMatch) -> bool:
    """Mirror index.html isFlyTime() — green fly detection."""
    margin = abs(match.home_score - match.away_score)
    p = match.period or 0
    c = match.clock_sec or 0
    sport = match.sport

    if sport == "basketball":
        return p >= 4 and c > 0 and c <= 300 and margin <= 8
    if sport == "football":
        return p >= 4 and c > 0 and c <= 300 and margin <= 8
    if sport == "hockey":
        return p >= 3 and c > 0 and c <= 300 and margin <= 1
    if sport == "baseball":
        return p >= 8 and margin <= 2
    if sport == "australian-football":
        if margin > 12:
            return False
        if p > 4:
            return True
        return p == 4 and c >= AFL_FLY_Q4_ELAPSED_SEC
    if sport in ("rugby-league", "rugby"):
        return p >= 2 and c > 0 and c <= 600 and margin <= 12
    if sport == "soccer":
        minute = 0
        try:
            minute = int(str(match.clock_raw).replace("'", "").split("+")[0].strip())
        except ValueError:
            minute = p
        return minute >= 80 and margin <= 1
    if sport == "cricket":
        req = match.cricket_runs_req
        overs = match.cricket_overs_left
        if req is None or overs is None:
            return False
        return req > 0 and req <= 20 and overs >= 0 and overs <= 2
    return False


def retroactive_flytime_from_final(
    home_score: int,
    away_score: int,
    close_margin: int,
) -> bool:
    """Proxy: game finished within close margin (offline research fallback)."""
    return abs(home_score - away_score) <= close_margin


def percentile_threshold(scores: list[float], percentile: float) -> float:
    """Top X% threshold — e.g. percentile=0.20 means top 20% of scores qualify."""
    if not scores:
        return 85.0
    sorted_scores = sorted(scores, reverse=True)
    idx = max(0, int(len(sorted_scores) * percentile) - 1)
    return sorted_scores[min(idx, len(sorted_scores) - 1)]
