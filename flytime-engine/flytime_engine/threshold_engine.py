"""Threshold learning and adaptive threshold evaluation."""
from __future__ import annotations

from statistics import mean
from typing import Optional

from .config import FORMULA_VERSIONS, PERCENTILE_CANDIDATES, THRESHOLD_CANDIDATES, LeagueConfig
from .db import Database, utcnow
from .flytime import FlyTimeEngine, percentile_threshold


class ThresholdEngine:
    """Evaluates fixed, percentile, and dynamic thresholds per league."""

    def __init__(self, db: Database, engine: FlyTimeEngine):
        self.db = db
        self.engine = engine

    def evaluate_league(
        self,
        league: LeagueConfig,
        league_id: int,
        formula_version: str = "v1",
    ) -> dict:
        """Compute metrics for current threshold and recommend adjustments."""
        rows = self.db.query_all(
            """SELECT m.had_yellow_fly, m.had_red_fly, m.home_team, m.away_team,
                      m.home_score, m.away_score, m.status
               FROM matches m
               JOIN leagues l ON l.id = m.league_id
               WHERE l.sport=? AND l.league_code=? AND m.status='finished'""",
            (league.sport, league.league_code),
        )

        yellow = sum(1 for r in rows if r["had_yellow_fly"])
        red = sum(1 for r in rows if r["had_red_fly"])
        total = len(rows)

        preds = self.db.query_all(
            """SELECT pr.flytime_score, pr.predicted_fly, pr.actual_fly,
                      pr.is_false_alarm, pr.is_miss, pr.is_hit
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE l.sport=? AND l.league_code=? AND pr.formula_version=?
                 AND m.status='finished'""",
            (league.sport, league.league_code, formula_version),
        )

        hits = sum(1 for p in preds if p["predicted_fly"] and p["actual_fly"])
        yellow_preds = sum(1 for p in preds if p["predicted_fly"])
        conversion = (hits / yellow_preds * 100) if yellow_preds else 0.0

        scores = [p["flytime_score"] for p in preds if p["flytime_score"] is not None]
        avg_score = mean(scores) if scores else 0.0
        winning_scores = [
            p["flytime_score"] for p in preds
            if p["flytime_score"] and p["actual_fly"]
        ]
        avg_winning = mean(winning_scores) if winning_scores else 0.0

        false_pos = sum(1 for p in preds if p["is_false_alarm"])
        false_neg = sum(1 for p in preds if p["is_miss"])

        # Simulate threshold candidates
        fixed_results = self._simulate_fixed_thresholds(league, formula_version)
        percentile_results = self._simulate_percentile_thresholds(scores)
        dynamic = self._dynamic_threshold(league, conversion, league.threshold or 85)

        best_fixed = max(fixed_results, key=lambda x: x["score"], default=None)
        recommended = best_fixed["threshold"] if best_fixed else (league.threshold or 85)

        result = {
            "league": league.label,
            "tag": league.tag,
            "current_threshold": league.threshold,
            "recommended_threshold": recommended,
            "yellow_flies": yellow,
            "red_flies": red,
            "conversion_pct": round(conversion, 2),
            "games_total": total,
            "fly_volume_per_round": round(yellow / max(total / league.chunk_size, 1), 2),
            "avg_flytime_score": round(avg_score, 2),
            "avg_winning_score": round(avg_winning, 2),
            "false_positives": false_pos,
            "false_negatives": false_neg,
            "fixed_analysis": fixed_results[:5],
            "percentile_analysis": percentile_results,
            "dynamic_threshold": dynamic,
            "expected_if_increase": self._expected_change(fixed_results, +3),
            "expected_if_decrease": self._expected_change(fixed_results, -3),
        }

        self._persist_threshold_history(league_id, league, result, formula_version)
        return result

    def evaluate_all(self, formula_version: str = "v1") -> list[dict]:
        from .config import LEAGUES
        results = []
        with self.db.session() as conn:
            for lg in LEAGUES:
                if not lg.flytime_file:
                    continue
                league_id = self.db.get_league_id(conn, lg.sport, lg.league_code)
                if league_id:
                    results.append(self.evaluate_league(lg, league_id, formula_version))
        return results

    def _simulate_fixed_thresholds(self, league: LeagueConfig, formula_version: str) -> list[dict]:
        preds = self.db.query_all(
            """SELECT pr.flytime_score, pr.actual_fly
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE l.sport=? AND l.league_code=? AND pr.formula_version=?
                 AND pr.flytime_score IS NOT NULL""",
            (league.sport, league.league_code, formula_version),
        )
        if not preds:
            return []

        results = []
        for thr in THRESHOLD_CANDIDATES:
            yellow = sum(1 for p in preds if p["flytime_score"] >= thr)
            red = sum(1 for p in preds if p["actual_fly"])
            hits = sum(1 for p in preds if p["flytime_score"] >= thr and p["actual_fly"])
            false_alarm = sum(1 for p in preds if p["flytime_score"] >= thr and not p["actual_fly"])
            missed = sum(1 for p in preds if p["flytime_score"] < thr and p["actual_fly"])
            conv = (hits / yellow * 100) if yellow else 0
            # Score: balance conversion vs volume target (~2 per chunk)
            volume_penalty = abs(yellow / max(len(preds) / league.chunk_size, 1) - 2)
            fitness = conv - volume_penalty * 5
            results.append({
                "threshold": thr,
                "yellow": yellow,
                "hits": hits,
                "conversion_pct": round(conv, 2),
                "false_positives": false_alarm,
                "false_negatives": missed,
                "score": fitness,
            })
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def _simulate_percentile_thresholds(self, scores: list[float]) -> list[dict]:
        results = []
        for pct in PERCENTILE_CANDIDATES:
            thr = percentile_threshold(scores, pct)
            yellow = sum(1 for s in scores if s >= thr)
            results.append({
                "percentile": pct,
                "threshold": round(thr, 2),
                "yellow_count": yellow,
                "pct_of_games": round(yellow / len(scores) * 100, 2) if scores else 0,
            })
        return results

    @staticmethod
    def _dynamic_threshold(league: LeagueConfig, conversion: float, current: float) -> float:
        """Adjust based on recent conversion rate."""
        if conversion > 60:
            return min(current + 3, 98)
        if conversion < 30 and conversion > 0:
            return max(current - 3, 65)
        return current

    @staticmethod
    def _expected_change(fixed_results: list[dict], delta: int) -> Optional[dict]:
        if not fixed_results:
            return None
        current_thr = fixed_results[0]["threshold"]
        target_thr = current_thr + delta
        match = next((r for r in fixed_results if r["threshold"] == target_thr), None)
        if match:
            return {
                "threshold": target_thr,
                "yellow": match["yellow"],
                "conversion_pct": match["conversion_pct"],
            }
        return {"threshold": target_thr, "note": "not in candidate set"}

    def _persist_threshold_history(
        self, league_id: int, league: LeagueConfig, result: dict, formula_version: str
    ) -> None:
        with self.db.session() as conn:
            conn.execute(
                """INSERT INTO threshold_history
                   (league_id, threshold_type, threshold_value, formula_version,
                    yellow_count, red_count, conversion_pct, fly_volume,
                    avg_flytime_score, avg_winning_score, recommended, notes)
                   VALUES (?, 'fixed', ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    league_id, result["recommended_threshold"], formula_version,
                    result["yellow_flies"], result["red_flies"], result["conversion_pct"],
                    result["fly_volume_per_round"], result["avg_flytime_score"],
                    result["avg_winning_score"],
                    f"current={league.threshold}, dynamic={result['dynamic_threshold']}",
                ),
            )
            conn.execute(
                """INSERT OR REPLACE INTO league_metrics
                   (league_id, period_start, period_end, formula_version, threshold,
                    games_total, yellow_flies, red_flies, conversion_pct,
                    false_positives, false_negatives, avg_flytime_score,
                    avg_winning_score, recommended_threshold)
                   VALUES (?, 'all-time', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    league_id, utcnow()[:10], formula_version, league.threshold,
                    result["games_total"], result["yellow_flies"], result["red_flies"],
                    result["conversion_pct"], result["false_positives"],
                    result["false_negatives"], result["avg_flytime_score"],
                    result["avg_winning_score"], result["recommended_threshold"],
                ),
            )
