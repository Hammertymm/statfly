"""Fly Intelligence analysis — accuracy, false positives/negatives, recommendations."""
from __future__ import annotations

from statistics import mean
from typing import Optional

from .db import Database
from .threshold_engine import ThresholdEngine
from .flytime import FlyTimeEngine
from .config import LEAGUES


class FlyIntelligence:
    """Automated intelligence reports for the Fly Intelligence Platform."""

    def __init__(self, db: Database, engine: Optional[FlyTimeEngine] = None):
        self.db = db
        self.engine = engine or FlyTimeEngine()
        self.engine.load_all(LEAGUES)
        self.threshold = ThresholdEngine(db, self.engine)

    def accuracy_report(self, formula_version: str = "v1") -> dict:
        """FlyScore prediction accuracy across all finished matches."""
        rows = self.db.query_all(
            """SELECT pr.predicted_fly, pr.actual_fly, pr.is_hit,
                      pr.is_false_alarm, pr.is_miss, pr.flytime_score, pr.threshold,
                      l.label as league, l.sport
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE pr.formula_version=? AND m.status='finished'""",
            (formula_version,),
        )
        total = len(rows)
        if not total:
            return {"formula_version": formula_version, "total_matches": 0}

        hits = sum(1 for r in rows if r["is_hit"])
        false_alarms = sum(1 for r in rows if r["is_false_alarm"])
        misses = sum(1 for r in rows if r["is_miss"])
        predicted = sum(1 for r in rows if r["predicted_fly"])
        actual = sum(1 for r in rows if r["actual_fly"])

        return {
            "formula_version": formula_version,
            "total_matches": total,
            "predicted_fly_count": predicted,
            "actual_fly_count": actual,
            "hits": hits,
            "false_positives": false_alarms,
            "false_negatives": misses,
            "precision_pct": round(hits / predicted * 100, 1) if predicted else 0,
            "recall_pct": round(hits / actual * 100, 1) if actual else 0,
            "accuracy_pct": round(hits / total * 100, 1),
            "f1_pct": round(
                2 * hits / (2 * hits + false_alarms + misses) * 100, 1
            ) if (hits + false_alarms + misses) else 0,
        }

    def fly_color_performance(self) -> dict:
        """Performance breakdown by fly colour (yellow/green/blue/red)."""
        totals = self.db.query_one(
            """SELECT
               SUM(had_yellow_fly) as yellow,
               SUM(had_live_flytime) as green,
               SUM(had_blue_fly) as blue,
               SUM(had_red_fly) as red,
               COUNT(*) as total_finished
               FROM matches WHERE status='finished'"""
        ) or {}

        yellow_to_red = self.db.query_one(
            """SELECT COUNT(*) as c FROM matches
               WHERE had_yellow_fly=1 AND had_red_fly=1 AND status='finished'"""
        )
        yellow_only = self.db.query_one(
            """SELECT COUNT(*) as c FROM matches
               WHERE had_yellow_fly=1 AND had_red_fly=0 AND status='finished'"""
        )
        green_no_yellow = self.db.query_one(
            """SELECT COUNT(*) as c FROM matches
               WHERE had_live_flytime=1 AND had_yellow_fly=0 AND status='finished'"""
        )

        y = totals.get("yellow") or 0
        g = totals.get("green") or 0
        b = totals.get("blue") or 0
        r = totals.get("red") or 0

        return {
            "yellow": {
                "count": y,
                "converted_to_red": (yellow_to_red or {}).get("c", 0),
                "conversion_pct": round((yellow_to_red or {}).get("c", 0) / y * 100, 1) if y else 0,
                "false_positive_count": (yellow_only or {}).get("c", 0),
            },
            "green": {
                "count": g,
                "missed_by_yellow": (green_no_yellow or {}).get("c", 0),
            },
            "blue": {
                "count": b,
                "became_red": self.db.query_one(
                    "SELECT SUM(became_red_fly) as c FROM blue_fly_events"
                ).get("c") or 0,
            },
            "red": {
                "count": r,
            },
            "total_finished": totals.get("total_finished") or 0,
        }

    def false_positive_analysis(self, formula_version: str = "v1", limit: int = 50) -> dict:
        """Matches where yellow was predicted but no live FlyTime occurred."""
        rows = self.db.query_all(
            """SELECT m.home_team, m.away_team, l.label as league, l.sport,
                      pr.flytime_score, pr.threshold, m.final_margin, m.finished_at
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE pr.formula_version=? AND pr.is_false_alarm=1 AND m.status='finished'
               ORDER BY m.finished_at DESC LIMIT ?""",
            (formula_version, limit),
        )
        by_league = {}
        for r in rows:
            key = r["league"]
            by_league.setdefault(key, {"count": 0, "avg_score": [], "avg_margin": []})
            by_league[key]["count"] += 1
            if r["flytime_score"]:
                by_league[key]["avg_score"].append(r["flytime_score"])
            if r["final_margin"] is not None:
                by_league[key]["avg_margin"].append(r["final_margin"])

        league_summary = [
            {
                "league": k,
                "count": v["count"],
                "avg_flyscore": round(mean(v["avg_score"]), 1) if v["avg_score"] else 0,
                "avg_final_margin": round(mean(v["avg_margin"]), 1) if v["avg_margin"] else 0,
            }
            for k, v in sorted(by_league.items(), key=lambda x: -x[1]["count"])
        ]

        return {
            "formula_version": formula_version,
            "total_false_positives": len(rows),
            "recent_examples": rows[:20],
            "by_league": league_summary,
        }

    def false_negative_analysis(self, formula_version: str = "v1", limit: int = 50) -> dict:
        """Matches with live FlyTime that were not predicted (yellow miss)."""
        rows = self.db.query_all(
            """SELECT m.home_team, m.away_team, l.label as league, l.sport,
                      pr.flytime_score, pr.threshold, m.final_margin, m.finished_at
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE pr.formula_version=? AND pr.is_miss=1 AND m.status='finished'
               ORDER BY m.finished_at DESC LIMIT ?""",
            (formula_version, limit),
        )
        return {
            "formula_version": formula_version,
            "total_false_negatives": len(rows),
            "recent_examples": rows[:20],
        }

    def threshold_recommendations(self) -> list[dict]:
        """Per-league threshold optimisation recommendations."""
        return self.threshold.evaluate_all()

    def pattern_insights(self) -> list[dict]:
        """Statistical correlations and pattern hints from collected data."""
        insights = []

        # High-conversion leagues
        high_conv = self.db.query_all(
            """SELECT l.label, l.sport, lm.conversion_pct, lm.yellow_flies, lm.red_flies
               FROM league_metrics lm
               JOIN leagues l ON l.id = lm.league_id
               WHERE lm.formula_version='v1' AND lm.period_start='all-time'
                 AND lm.yellow_flies >= 10
               ORDER BY lm.conversion_pct DESC LIMIT 5"""
        )
        if high_conv:
            best = high_conv[0]
            insights.append({
                "type": "high_conversion_league",
                "message": f"{best['label']} has {best['conversion_pct']:.1f}% yellow→red conversion "
                           f"({best['yellow_flies']} yellow, {best['red_flies']} red)",
                "data": best,
            })

        # Low-conversion leagues needing threshold raise
        low_conv = self.db.query_all(
            """SELECT l.label, l.threshold as current, lm.recommended_threshold,
                      lm.conversion_pct, lm.yellow_flies
               FROM league_metrics lm
               JOIN leagues l ON l.id = lm.league_id
               WHERE lm.formula_version='v1' AND lm.period_start='all-time'
                 AND lm.yellow_flies >= 10 AND lm.conversion_pct < 15
               ORDER BY lm.conversion_pct ASC LIMIT 5"""
        )
        for row in low_conv:
            insights.append({
                "type": "threshold_raise_candidate",
                "message": f"{row['label']}: {row['conversion_pct']:.1f}% conversion — "
                           f"consider raising threshold from {row['current']} to {row['recommended_threshold']}",
                "data": row,
            })

        # Formula comparison
        formulas = self.db.query_all(
            """SELECT formula_version,
                      AVG(CASE WHEN is_hit THEN 1.0 ELSE 0.0 END) * 100 as hit_rate,
                      COUNT(*) as n
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               WHERE m.status='finished'
               GROUP BY formula_version HAVING n >= 20
               ORDER BY hit_rate DESC"""
        )
        if len(formulas) >= 2:
            best_f = formulas[0]
            prod = next((f for f in formulas if f["formula_version"] == "v1"), None)
            if prod and best_f["formula_version"] != "v1":
                insights.append({
                    "type": "formula_improvement",
                    "message": f"{best_f['formula_version']} outperforms v1 "
                               f"({best_f['hit_rate']:.1f}% vs {prod['hit_rate']:.1f}% hit rate)",
                    "data": {"best": best_f, "production": prod},
                })

        # Snapshot density for live matches
        snap_stats = self.db.query_one(
            """SELECT AVG(cnt) as avg_snapshots, MAX(cnt) as max_snapshots
               FROM (SELECT match_id, COUNT(*) as cnt FROM live_snapshots GROUP BY match_id)"""
        )
        if snap_stats and snap_stats.get("avg_snapshots"):
            insights.append({
                "type": "snapshot_coverage",
                "message": f"Average {snap_stats['avg_snapshots']:.0f} snapshots per live match "
                           f"(max {snap_stats['max_snapshots']})",
                "data": snap_stats,
            })

        return insights

    def formula_improvement_suggestions(self) -> list[dict]:
        """Suggested formula weight adjustments based on backtest data."""
        suggestions = []
        rankings = self.db.query_all(
            """SELECT formula_version,
                      SUM(CASE WHEN is_hit THEN 1 ELSE 0 END) as hits,
                      SUM(CASE WHEN is_false_alarm THEN 1 ELSE 0 END) as fp,
                      SUM(CASE WHEN is_miss THEN 1 ELSE 0 END) as fn,
                      COUNT(*) as total
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               WHERE m.status='finished'
               GROUP BY formula_version"""
        )
        if not rankings:
            return suggestions

        best = max(rankings, key=lambda r: r["hits"] / r["total"] if r["total"] else 0)
        if best["formula_version"] != "v1" and best["total"] >= 50:
            suggestions.append({
                "priority": "medium",
                "action": f"Consider promoting {best['formula_version']} to production",
                "evidence": f"{best['hits']}/{best['total']} hits "
                            f"({best['hits']/best['total']*100:.1f}%)",
            })

        fp_leagues = self.db.query_all(
            """SELECT l.label, COUNT(*) as fp_count
               FROM prediction_results pr
               JOIN matches m ON m.id = pr.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE pr.formula_version='v1' AND pr.is_false_alarm=1 AND m.status='finished'
               GROUP BY l.label ORDER BY fp_count DESC LIMIT 3"""
        )
        for row in fp_leagues:
            if row["fp_count"] >= 5:
                suggestions.append({
                    "priority": "high",
                    "action": f"Raise yellow threshold for {row['label']}",
                    "evidence": f"{row['fp_count']} false positives in v1",
                })

        return suggestions

    def full_intelligence_report(self) -> dict:
        """Complete intelligence package for dashboard and API."""
        return {
            "accuracy": self.accuracy_report("v1"),
            "accuracy_by_formula": {
                fv: self.accuracy_report(fv)
                for fv in ("v1", "v2", "v3", "experimental")
            },
            "fly_color_performance": self.fly_color_performance(),
            "false_positives": self.false_positive_analysis(),
            "false_negatives": self.false_negative_analysis(),
            "threshold_recommendations": self.threshold_recommendations()[:20],
            "pattern_insights": self.pattern_insights(),
            "formula_suggestions": self.formula_improvement_suggestions(),
        }
