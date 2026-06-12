"""Analytics and reporting for the FlyTime Data Engine."""
from __future__ import annotations

import json
from pathlib import Path

from .blue_fly import BlueFlyAnalyzer
from .config import LEAGUES
from .db import Database
from .flytime import FlyTimeEngine
from .formula_testing import FormulaTester
from .threshold_engine import ThresholdEngine


class Analytics:
    """Generates league overview, threshold, formula, and blue fly reports."""

    def __init__(self, db: Database):
        self.db = db
        self.engine = FlyTimeEngine()
        self.engine.load_all(LEAGUES)
        self.threshold = ThresholdEngine(db, self.engine)
        self.formula = FormulaTester(db, self.engine)
        self.blue_fly = BlueFlyAnalyzer(db)

    def league_overview(self) -> list[dict]:
        rows = self.db.query_all(
            """SELECT l.label, l.tag, l.threshold as current_threshold,
                      lm.recommended_threshold, lm.yellow_flies, lm.red_flies,
                      lm.conversion_pct, lm.games_total
               FROM leagues l
               LEFT JOIN league_metrics lm ON lm.league_id = l.id
                    AND lm.formula_version = 'v1' AND lm.period_start = 'all-time'
               WHERE l.flytime_file IS NOT NULL
               ORDER BY l.label"""
        )
        if not rows or all(r["yellow_flies"] is None for r in rows):
            return self.threshold.evaluate_all()
        return rows

    def threshold_analysis(self) -> dict:
        all_evals = self.threshold.evaluate_all()
        if not all_evals:
            return {"best": None, "worst": None, "leagues": []}
        by_conv = sorted(all_evals, key=lambda x: x.get("conversion_pct", 0), reverse=True)
        return {
            "best_threshold_league": by_conv[0] if by_conv else None,
            "worst_threshold_league": by_conv[-1] if by_conv else None,
            "leagues": all_evals,
        }

    def formula_analysis(self) -> dict:
        rankings = self.formula.rank_formulas()
        league_rankings = self.formula.compare_all_leagues("v1")
        return {
            "formula_rankings": rankings,
            "league_rankings_v1": league_rankings[:15],
            "production_formula": "v1",
        }

    def blue_fly_analysis(self) -> dict:
        return self.blue_fly.full_report()

    def service_health(self) -> dict:
        return {
            "status": self.db.get_service_state("service_status") or "not_started",
            "started_at": self.db.get_service_state("service_started_at"),
            "last_poll_at": self.db.get_service_state("last_poll_at"),
            "last_error": self.db.get_service_state("last_error"),
            "match_counts": self.db.query_one(
                """SELECT
                   SUM(CASE WHEN status='upcoming' THEN 1 ELSE 0 END) as upcoming,
                   SUM(CASE WHEN status='live' THEN 1 ELSE 0 END) as live,
                   SUM(CASE WHEN status='finished' THEN 1 ELSE 0 END) as finished,
                   COUNT(*) as total
                   FROM matches"""
            ),
            "fly_counts": self.db.query_one(
                """SELECT
                   SUM(had_yellow_fly) as yellow,
                   SUM(had_live_flytime) as green,
                   SUM(had_blue_fly) as blue,
                   SUM(had_red_fly) as red
                   FROM matches"""
            ),
            "snapshot_count": self.db.query_one(
                "SELECT COUNT(*) as c FROM live_snapshots"
            ),
            "event_count": self.db.query_one(
                "SELECT COUNT(*) as c FROM match_events"
            ),
        }

    def full_report(self) -> dict:
        return {
            "health": self.service_health(),
            "league_overview": self.league_overview(),
            "threshold_analysis": self.threshold_analysis(),
            "formula_analysis": self.formula_analysis(),
            "blue_fly_analysis": self.blue_fly_analysis(),
        }

    def export_report(self, path: Path) -> None:
        report = self.full_report()
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    def print_summary(self) -> None:
        health = self.service_health()
        mc = health.get("match_counts") or {}
        fc = health.get("fly_counts") or {}
        print("\n=== FlyTime Data Engine - Analytics Summary ===")
        print(f"Service: {health['status']}  |  Last poll: {health.get('last_poll_at', 'never')}")
        print(f"Matches: {mc.get('total', 0)} total  ({mc.get('live', 0)} live, {mc.get('finished', 0)} finished)")
        print(f"Flies:   {fc.get('yellow', 0)} yellow  {fc.get('green', 0)} green  "
              f"{fc.get('blue', 0)} blue  {fc.get('red', 0)} red")
        print(f"Snapshots: {(health.get('snapshot_count') or {}).get('c', 0)}  "
              f"Events: {(health.get('event_count') or {}).get('c', 0)}")

        overview = self.league_overview()
        if overview:
            print("\n-- League Overview (top 10 by yellow flies) --")
            top = sorted(overview, key=lambda x: x.get("yellow_flies", 0) or 0, reverse=True)[:10]
            for r in top:
                print(f"  {r.get('league') or r.get('label', '?'):20s}  "
                      f"thr={r.get('current_threshold', '?'):>3}  "
                      f"rec={r.get('recommended_threshold', '?'):>3}  "
                      f"Y={r.get('yellow_flies', 0):>4}  R={r.get('red_flies', 0):>4}  "
                      f"conv={r.get('conversion_pct', 0):>5.1f}%")

        bf = self.blue_fly.overall_stats()
        print(f"\n-- Blue Fly --  total={bf.get('total_blue_flies', 0)}  "
              f"-> red={bf.get('became_red_fly', 0)}  ({bf.get('conversion_pct', 0)}%)")

        formulas = self.formula.rank_formulas()
        if formulas:
            print("\n-- Formula Rankings --")
            for f in formulas:
                print(f"  {f['formula_version']:12s}  conv={f['avg_conversion_pct']:>5.1f}%  "
                      f"Y={f['total_yellow']:>5}  leagues={f['leagues_tested']}")
