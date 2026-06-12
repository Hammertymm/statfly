"""Multi-formula backtesting framework."""
from __future__ import annotations

import json
from statistics import mean

from .config import FORMULA_VERSIONS, THRESHOLD_CANDIDATES, LeagueConfig
from .db import Database, utcnow
from .flytime import FlyTimeEngine


class FormulaTester:
    """Replay historical matches across formula versions and thresholds."""

    def __init__(self, db: Database, engine: FlyTimeEngine):
        self.db = db
        self.engine = engine

    def backtest_league(
        self,
        league: LeagueConfig,
        formula_version: str = "v1",
        threshold: float | None = None,
        season_label: str | None = None,
    ) -> dict:
        thr = threshold or league.threshold or 85.0
        idx = self.engine.load_league(league)
        if not idx:
            return {"league": league.label, "error": "no flytime table"}

        sql = """SELECT m.id, m.home_team, m.away_team, m.home_score, m.away_score,
                        m.had_red_fly, m.season
                 FROM matches m JOIN leagues l ON l.id = m.league_id
                 WHERE l.sport=? AND l.league_code=? AND m.status='finished'"""
        params: list = [league.sport, league.league_code]
        if season_label:
            sql += " AND m.season=?"
            params.append(season_label)
        rows = self.db.query_all(sql, tuple(params))

        yellow = red = hits = false_pos = false_neg = 0
        scores = []

        for row in rows:
            from .espn import ParsedMatch
            m = ParsedMatch(
                espn_event_id=str(row["id"]),
                sport=league.sport,
                league_code=league.league_code,
                home_team=row["home_team"],
                away_team=row["away_team"],
                home_team_id="", away_team_id="",
                status="finished",
                scheduled_at="",
                home_score=row["home_score"] or 0,
                away_score=row["away_score"] or 0,
            )
            result = self.engine.score_matchup(
                m.home_team, m.away_team, idx, thr, formula_version
            )
            if result.score is None:
                continue
            scores.append(result.score)
            actual = bool(row["had_red_fly"])
            predicted = result.score >= thr
            if predicted:
                yellow += 1
            if actual:
                red += 1
            if predicted and actual:
                hits += 1
            if predicted and not actual:
                false_pos += 1
            if not predicted and actual:
                false_neg += 1

        conversion = (hits / yellow * 100) if yellow else 0
        result = {
            "league": league.label,
            "formula_version": formula_version,
            "threshold": thr,
            "season": season_label or "all",
            "games_tested": len(rows),
            "yellow_count": yellow,
            "red_count": red,
            "hits": hits,
            "conversion_pct": round(conversion, 2),
            "false_positives": false_pos,
            "false_negatives": false_neg,
            "avg_score": round(mean(scores), 2) if scores else 0,
        }

        with self.db.session() as conn:
            league_id = self.db.get_league_id(conn, league.sport, league.league_code)
            if league_id:
                conn.execute(
                    """INSERT INTO historical_backtests
                       (league_id, formula_version, threshold, threshold_type, season_label,
                        games_tested, yellow_count, red_count, conversion_pct,
                        false_positives, false_negatives, avg_score, config_json)
                       VALUES (?, ?, ?, 'fixed', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        league_id, formula_version, thr, season_label,
                        result["games_tested"], yellow, red, conversion,
                        false_pos, false_neg, result["avg_score"],
                        json.dumps({"formula": formula_version, "threshold": thr}),
                    ),
                )
        return result

    def compare_formulas(self, league: LeagueConfig) -> list[dict]:
        return [
            self.backtest_league(league, fv)
            for fv in FORMULA_VERSIONS
        ]

    def compare_all_leagues(self, formula_version: str = "v1") -> list[dict]:
        from .config import LEAGUES
        results = []
        for lg in LEAGUES:
            if lg.flytime_file:
                results.append(self.backtest_league(lg, formula_version))
        return sorted(results, key=lambda x: x.get("conversion_pct", 0), reverse=True)

    def rank_formulas(self) -> list[dict]:
        """Global formula rankings across all leagues."""
        rankings = []
        for fv in FORMULA_VERSIONS:
            results = self.compare_all_leagues(fv)
            if not results:
                continue
            avg_conv = mean(r["conversion_pct"] for r in results if r.get("conversion_pct"))
            total_yellow = sum(r["yellow_count"] for r in results)
            total_red = sum(r["red_count"] for r in results)
            rankings.append({
                "formula_version": fv,
                "name": FORMULA_VERSIONS[fv]["name"],
                "avg_conversion_pct": round(avg_conv, 2),
                "total_yellow": total_yellow,
                "total_red": total_red,
                "leagues_tested": len(results),
            })
        return sorted(rankings, key=lambda x: x["avg_conversion_pct"], reverse=True)

    def sweep_thresholds(self, league: LeagueConfig, formula_version: str = "v1") -> list[dict]:
        return [
            self.backtest_league(league, formula_version, thr)
            for thr in THRESHOLD_CANDIDATES
        ]
