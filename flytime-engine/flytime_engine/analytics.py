"""Analytics and reporting for the FlyTime Data Engine."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .blue_fly import BlueFlyAnalyzer
from .config import LEAGUES
from .db import Database
from .flytime import FlyTimeEngine
from .formula_testing import FormulaTester
from .intelligence import FlyIntelligence
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
            "live_matches": self.live_matches(),
            "recent_events": self.recent_events(),
        }

    def recommendations(self) -> dict:
        """Per-league threshold recommendations for PWA sync."""
        evals = self.threshold.evaluate_all()
        leagues = {}
        for row in evals:
            key = row.get("league") or row.get("label", "")
            leagues[key] = {
                "sport": row.get("sport"),
                "league_code": row.get("league_code"),
                "current_threshold": row.get("current_threshold"),
                "recommended_threshold": row.get("recommended_threshold"),
                "threshold_type": row.get("recommended_type", "fixed"),
                "conversion_pct": row.get("conversion_pct"),
                "yellow_flies": row.get("yellow_flies"),
                "red_flies": row.get("red_flies"),
            }
        return {
            "generated_at": self.db.get_service_state("last_poll_at"),
            "formula_version": "v1",
            "leagues": leagues,
        }

    def live_matches(self) -> list[dict]:
        """Currently tracked live and upcoming matches with latest state."""
        rows = self.db.query_all(
            """SELECT m.id, m.espn_event_id, m.home_team, m.away_team,
                      m.home_score, m.away_score, m.status, m.scheduled_at,
                      m.had_yellow_fly, m.had_live_flytime, m.had_blue_fly,
                      l.label as league, l.sport, l.tag,
                      ls.period, ls.clock_raw, ls.clock_sec, ls.margin,
                      ls.is_flytime, ls.flytime_score, ls.threshold,
                      ls.captured_at as last_snapshot_at
               FROM matches m
               JOIN leagues l ON l.id = m.league_id
               LEFT JOIN live_snapshots ls ON ls.id = (
                   SELECT id FROM live_snapshots
                   WHERE match_id = m.id ORDER BY captured_at DESC LIMIT 1
               )
               WHERE m.status IN ('live', 'upcoming')
               ORDER BY
                 CASE m.status WHEN 'live' THEN 0 ELSE 1 END,
                 m.scheduled_at ASC"""
        )
        result = []
        for r in rows:
            fly_class = self._classify_fly(r)
            result.append({
                **r,
                "fly_classification": fly_class,
                "in_flytime": bool(r.get("is_flytime")) or bool(r.get("had_live_flytime")),
                "score_display": f"{r.get('home_score') or 0}-{r.get('away_score') or 0}",
            })
        return result

    def _classify_fly(self, match: dict) -> str:
        if match.get("status") == "live" and match.get("is_flytime"):
            if match.get("had_yellow_fly"):
                return "blue"
            return "green"
        if match.get("status") == "upcoming" and match.get("had_yellow_fly"):
            return "yellow"
        if match.get("had_yellow_fly") and not match.get("had_live_flytime"):
            return "yellow"
        return "none"

    def recent_events(self, limit: int = 40) -> list[dict]:
        """Recent fly triggers and state transitions."""
        return self.db.query_all(
            """SELECT e.event_at, e.event_type, e.match_state,
                      e.home_score, e.away_score, e.period, e.clock_raw,
                      e.flytime_score, e.threshold,
                      m.home_team, m.away_team, l.label as league, l.sport
               FROM match_events e
               JOIN matches m ON m.id = e.match_id
               JOIN leagues l ON l.id = m.league_id
               WHERE e.event_type IN (
                   'yellow_fly', 'green_fly', 'green_fly_exit',
                   'blue_fly', 'red_fly', 'score_change', 'match_start', 'match_end'
               )
               ORDER BY e.event_at DESC LIMIT ?""",
            (limit,),
        )

    def flytime_matches(self) -> list[dict]:
        """Matches currently in live FlyTime."""
        return [m for m in self.live_matches() if m.get("in_flytime")]

    def conversion_rates(self) -> dict:
        """Conversion rates by fly colour."""
        intel = FlyIntelligence(self.db, self.engine)
        return intel.fly_color_performance()

    def historical_trends(self, days: int = 30) -> list[dict]:
        """Daily fly counts over time."""
        return self.db.query_all(
            """SELECT DATE(COALESCE(finished_at, scheduled_at)) as day,
                      SUM(had_yellow_fly) as yellow,
                      SUM(had_live_flytime) as green,
                      SUM(had_blue_fly) as blue,
                      SUM(had_red_fly) as red,
                      COUNT(*) as matches
               FROM matches
               WHERE status='finished'
                 AND finished_at >= datetime('now', ?)
               GROUP BY day ORDER BY day""",
            (f"-{days} days",),
        )

    def sport_breakdown(self) -> list[dict]:
        """Performance metrics grouped by sport."""
        return self.db.query_all(
            """SELECT l.sport,
                      COUNT(*) as total_matches,
                      SUM(m.had_yellow_fly) as yellow,
                      SUM(m.had_live_flytime) as green,
                      SUM(m.had_blue_fly) as blue,
                      SUM(m.had_red_fly) as red,
                      ROUND(AVG(CASE WHEN m.had_yellow_fly AND m.had_red_fly THEN 1.0 ELSE 0.0 END) * 100, 1) as yellow_to_red_pct
               FROM matches m
               JOIN leagues l ON l.id = m.league_id
               WHERE m.status='finished'
               GROUP BY l.sport ORDER BY total_matches DESC"""
        )

    def research_query(
        self,
        *,
        league: str | None = None,
        sport: str | None = None,
        status: str | None = None,
        had_yellow: bool | None = None,
        had_green: bool | None = None,
        formula_version: str = "v1",
        limit: int = 200,
    ) -> list[dict]:
        """Filterable historical match data for research mode."""
        clauses = ["1=1"]
        params: list = []

        if league:
            clauses.append("l.label = ?")
            params.append(league)
        if sport:
            clauses.append("l.sport = ?")
            params.append(sport)
        if status:
            clauses.append("m.status = ?")
            params.append(status)
        if had_yellow is not None:
            clauses.append(f"m.had_yellow_fly = ?")
            params.append(int(had_yellow))
        if had_green is not None:
            clauses.append(f"m.had_live_flytime = ?")
            params.append(int(had_green))

        params.append(limit)
        where = " AND ".join(clauses)

        return self.db.query_all(
            f"""SELECT m.id, m.espn_event_id, m.home_team, m.away_team,
                       m.status, m.scheduled_at, m.finished_at,
                       m.home_score, m.away_score, m.final_margin,
                       m.had_yellow_fly, m.had_live_flytime, m.had_blue_fly, m.had_red_fly,
                       l.label as league, l.sport,
                       pr.flytime_score, pr.threshold, pr.formula_version,
                       pr.predicted_fly, pr.actual_fly, pr.is_hit,
                       pr.is_false_alarm, pr.is_miss,
                       (SELECT COUNT(*) FROM live_snapshots WHERE match_id=m.id) as snapshots
                FROM matches m
                JOIN leagues l ON l.id = m.league_id
                LEFT JOIN prediction_results pr ON pr.match_id=m.id AND pr.formula_version=?
                WHERE {where}
                ORDER BY m.scheduled_at DESC LIMIT ?""",
            (formula_version, *params),
        )

    def match_detail(self, match_id: int) -> dict | None:
        """Full match detail with events and snapshots."""
        match = self.db.query_one(
            """SELECT m.*, l.label as league, l.sport, l.tag
               FROM matches m JOIN leagues l ON l.id = m.league_id
               WHERE m.id=?""",
            (match_id,),
        )
        if not match:
            return None

        events = self.db.query_all(
            "SELECT * FROM match_events WHERE match_id=? ORDER BY event_at",
            (match_id,),
        )
        snapshots = self.db.query_all(
            "SELECT * FROM live_snapshots WHERE match_id=? ORDER BY captured_at",
            (match_id,),
        )
        predictions = self.db.query_all(
            "SELECT * FROM prediction_results WHERE match_id=?",
            (match_id,),
        )
        fly_events = self.db.query_all(
            "SELECT * FROM fly_events WHERE match_id=? ORDER BY activated_at",
            (match_id,),
        )

        return {
            "match": match,
            "events": events,
            "snapshots": snapshots,
            "predictions": predictions,
            "fly_events": fly_events,
        }

    def export_csv(self, rows: list[dict]) -> str:
        """Export research rows to CSV string."""
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def compare_formulas(self, league: str | None = None) -> list[dict]:
        """Compare formula versions for research mode."""
        clause = ""
        params: tuple = ()
        if league:
            clause = "AND l.label = ?"
            params = (league,)

        return self.db.query_all(
            f"""SELECT pr.formula_version,
                       COUNT(*) as total,
                       SUM(pr.is_hit) as hits,
                       SUM(pr.is_false_alarm) as false_positives,
                       SUM(pr.is_miss) as false_negatives,
                       ROUND(AVG(pr.flytime_score), 1) as avg_score
                FROM prediction_results pr
                JOIN matches m ON m.id = pr.match_id
                JOIN leagues l ON l.id = m.league_id
                WHERE m.status='finished' {clause}
                GROUP BY pr.formula_version
                ORDER BY hits DESC""",
            params,
        )

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
