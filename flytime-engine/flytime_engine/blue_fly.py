"""Blue Fly analysis engine."""
from __future__ import annotations

from statistics import mean

from .db import Database


class BlueFlyAnalyzer:
    """Analyses Blue Fly (yellow → green) behaviour and outcomes."""

    def __init__(self, db: Database):
        self.db = db

    def league_breakdown(self) -> list[dict]:
        return self.db.query_all(
            """SELECT l.label, l.tag, COUNT(*) as blue_count,
                      SUM(became_red_fly) as red_conversions,
                      ROUND(100.0 * SUM(became_red_fly) / COUNT(*), 2) as conversion_pct,
                      ROUND(AVG(yellow_score), 2) as avg_yellow_score,
                      ROUND(AVG(score_differential), 2) as avg_margin_at_activation,
                      ROUND(AVG(time_remaining_sec), 0) as avg_time_remaining
               FROM blue_fly_events b
               JOIN leagues l ON l.id = b.league_id
               GROUP BY l.id
               ORDER BY blue_count DESC"""
        )

    def overall_stats(self) -> dict:
        row = self.db.query_one(
            """SELECT COUNT(*) as total,
                      SUM(became_red_fly) as became_red,
                      ROUND(100.0 * SUM(became_red_fly) / COUNT(*), 2) as conversion_pct
               FROM blue_fly_events"""
        )
        if not row or not row["total"]:
            return {
                "total_blue_flies": 0,
                "became_red_fly": 0,
                "conversion_pct": 0,
                "message": "No blue fly events recorded yet. Run live collection during games.",
            }
        return {
            "total_blue_flies": row["total"],
            "became_red_fly": row["became_red"] or 0,
            "conversion_pct": row["conversion_pct"] or 0,
            "how_often_blue_becomes_red": f"{row['conversion_pct'] or 0}%",
        }

    def threshold_performance(self) -> list[dict]:
        """Which thresholds produce the best blue → red conversion."""
        return self.db.query_all(
            """SELECT ROUND(yellow_threshold, 0) as threshold,
                      COUNT(*) as blue_count,
                      SUM(became_red_fly) as red_count,
                      ROUND(100.0 * SUM(became_red_fly) / COUNT(*), 2) as conversion_pct
               FROM blue_fly_events
               GROUP BY ROUND(yellow_threshold, 0)
               ORDER BY conversion_pct DESC"""
        )

    def patterns_before_success(self) -> dict:
        """Patterns in successful vs unsuccessful blue flies."""
        success = self.db.query_all(
            """SELECT yellow_score, score_differential, time_remaining_sec, period
               FROM blue_fly_events WHERE became_red_fly=1"""
        )
        failure = self.db.query_all(
            """SELECT yellow_score, score_differential, time_remaining_sec, period
               FROM blue_fly_events WHERE became_red_fly=0"""
        )

        def avg_field(rows, field):
            vals = [r[field] for r in rows if r[field] is not None]
            return round(mean(vals), 2) if vals else None

        return {
            "successful_blue_flies": len(success),
            "unsuccessful_blue_flies": len(failure),
            "success_patterns": {
                "avg_yellow_score": avg_field(success, "yellow_score"),
                "avg_margin_at_activation": avg_field(success, "score_differential"),
                "avg_time_remaining_sec": avg_field(success, "time_remaining_sec"),
                "avg_period": avg_field(success, "period"),
            },
            "failure_patterns": {
                "avg_yellow_score": avg_field(failure, "yellow_score"),
                "avg_margin_at_activation": avg_field(failure, "score_differential"),
                "avg_time_remaining_sec": avg_field(failure, "time_remaining_sec"),
                "avg_period": avg_field(failure, "period"),
            },
            "can_blue_fly_be_predictive": (
                "Yes — track conversion rate by league and threshold. "
                "High blue→red conversion suggests yellow predictions are well-calibrated."
                if success else "Insufficient data — need live collection."
            ),
        }

    def full_report(self) -> dict:
        return {
            "overall": self.overall_stats(),
            "by_league": self.league_breakdown(),
            "by_threshold": self.threshold_performance(),
            "patterns": self.patterns_before_success(),
        }
