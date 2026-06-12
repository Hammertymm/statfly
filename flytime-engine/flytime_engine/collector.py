"""Historical backfill and live match collection."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import (
    LEAGUES,
    POLL_FAST_SEC,
    POLL_FLYTIME_SEC,
    POLL_IDLE_SEC,
    LeagueConfig,
    get_season_windows,
)
from .db import Database, utcnow
from .espn import ParsedMatch, fetch_daily, fetch_live_window, fetch_scoreboard
from .flytime import FlyTimeEngine, is_flytime_live, retroactive_flytime_from_final


class MatchCollector:
    """Ingests ESPN data into the FlyTime database."""

    def __init__(self, db: Database, engine: FlyTimeEngine):
        self.db = db
        self.engine = engine
        self._live_state: dict[int, dict] = {}  # match_id -> last known state

    def backfill_league(self, league: LeagueConfig, force: bool = False) -> int:
        """Import historical finished matches for one league."""
        windows = get_season_windows(league)
        total = 0
        normalize = league.normalize

        with self.db.session() as conn:
            league_id = self.db.get_league_id(conn, league.sport, league.league_code)
            if not league_id:
                return 0

            for label, start, end in windows:
                existing = conn.execute(
                    """SELECT status FROM backfill_progress
                       WHERE league_id=? AND date_range_start=? AND date_range_end=?""",
                    (league_id, start, end),
                ).fetchone()
                if existing and existing["status"] == "done" and not force:
                    continue

                conn.execute(
                    """INSERT INTO backfill_progress
                       (league_id, date_range_start, date_range_end, status, started_at)
                       VALUES (?, ?, ?, 'running', ?)
                       ON CONFLICT(league_id, date_range_start, date_range_end)
                       DO UPDATE SET status='running', started_at=excluded.started_at""",
                    (league_id, start, end, utcnow()),
                )

                try:
                    if league.daily_ranges:
                        matches = fetch_daily(league.sport, league.league_code, start, end, normalize)
                    else:
                        matches = fetch_scoreboard(league.sport, league.league_code, start, end, normalize)

                    imported = 0
                    for m in matches:
                        if m.status != "finished":
                            continue
                        n = self._store_match(conn, league, league_id, m, historical=True)
                        if n:
                            imported += 1
                    total += imported

                    conn.execute(
                        """UPDATE backfill_progress SET status='done', games_imported=?,
                           finished_at=? WHERE league_id=? AND date_range_start=? AND date_range_end=?""",
                        (imported, utcnow(), league_id, start, end),
                    )
                except Exception as e:
                    conn.execute(
                        """UPDATE backfill_progress SET status='failed', error_message=?,
                           finished_at=? WHERE league_id=? AND date_range_start=? AND date_range_end=?""",
                        (str(e), utcnow(), league_id, start, end),
                    )
                    raise

        return total

    def backfill_all(self, force: bool = False) -> dict[str, int]:
        results = {}
        for lg in LEAGUES:
            try:
                n = self.backfill_league(lg, force=force)
                results[lg.label] = n
                print(f"  {lg.label}: {n} historical matches", flush=True)
            except Exception as e:
                results[lg.label] = -1
                print(f"  {lg.label}: FAILED — {e}", flush=True)
            time.sleep(0.2)
        return results

    def poll_league(self, league: LeagueConfig) -> int:
        """Poll live window for one league and process all matches."""
        matches = fetch_live_window(
            league.sport, league.league_code, league.normalize, days_back=7, days_fwd=2
        )
        count = 0
        with self.db.session() as conn:
            league_id = self.db.get_league_id(conn, league.sport, league.league_code)
            if not league_id:
                return 0
            for m in matches:
                self._process_match(conn, league, league_id, m)
                count += 1
        return count

    def poll_all(self) -> dict[str, int]:
        results = {}
        any_live_flytime = False

        for lg in LEAGUES:
            try:
                n = self.poll_league(lg)
                results[lg.label] = n
            except Exception as e:
                results[lg.label] = -1
                print(f"Poll {lg.label} failed: {e}", flush=True)

        with self.db.session() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM matches WHERE status='live' AND had_live_flytime=1"
            ).fetchone()
            any_live_flytime = row["c"] > 0

        self.db.set_service_state("last_poll_at", utcnow())
        self.db.set_service_state("any_live_flytime", "1" if any_live_flytime else "0")
        return results

    def _store_match(
        self,
        conn,
        league: LeagueConfig,
        league_id: int,
        m: ParsedMatch,
        historical: bool = False,
    ) -> bool:
        match_id = self.db.upsert_match(
            conn,
            espn_event_id=m.espn_event_id,
            league_id=league_id,
            home_team=m.home_team,
            away_team=m.away_team,
            scheduled_at=m.scheduled_at,
            status=m.status,
            home_score=m.home_score,
            away_score=m.away_score,
            season=m.season,
            venue=m.venue,
            home_team_id=m.home_team_id,
            away_team_id=m.away_team_id,
        )

        if historical and m.status == "finished":
            had_red = retroactive_flytime_from_final(
                m.home_score, m.away_score, league.close_margin
            )
            if had_red:
                self.db.update_match_flags(conn, match_id, had_live_flytime=1, had_red_fly=1)
                self._record_prediction(conn, match_id, league, m, actual_fly=True)

            ft_result = self.engine.score_for_league(m, league)
            if ft_result.is_yellow:
                self.db.update_match_flags(conn, match_id, had_yellow_fly=1)
                self._record_prediction(conn, match_id, league, m, actual_fly=had_red)

        return True

    def _process_match(
        self,
        conn,
        league: LeagueConfig,
        league_id: int,
        m: ParsedMatch,
    ) -> None:
        match_id = self.db.upsert_match(
            conn,
            espn_event_id=m.espn_event_id,
            league_id=league_id,
            home_team=m.home_team,
            away_team=m.away_team,
            scheduled_at=m.scheduled_at,
            status=m.status,
            home_score=m.home_score,
            away_score=m.away_score,
            season=m.season,
            venue=m.venue,
            home_team_id=m.home_team_id,
            away_team_id=m.away_team_id,
        )

        prev = self._live_state.get(match_id, {})
        ft_result = self.engine.score_for_league(m, league)
        is_green = is_flytime_live(m) if m.status == "live" else False
        is_yellow = ft_result.is_yellow and m.status == "upcoming"
        was_yellow = prev.get("had_yellow", False)
        was_green = prev.get("had_green", False)

        # Status change events
        if prev.get("status") and prev["status"] != m.status:
            self.db.log_event(
                conn, match_id=match_id, event_type="status_change",
                match_state=m.status, home_score=m.home_score, away_score=m.away_score,
                detail={"from": prev["status"], "to": m.status},
            )
            if m.status == "live":
                self.db.log_event(conn, match_id=match_id, event_type="match_start", match_state="live")
            if m.status == "finished":
                self.db.log_event(conn, match_id=match_id, event_type="match_end", match_state="finished")

        # Score change
        if (prev.get("home_score") != m.home_score or prev.get("away_score") != m.away_score) and m.status == "live":
            self.db.log_event(
                conn, match_id=match_id, event_type="score_change",
                match_state="live", home_score=m.home_score, away_score=m.away_score,
                period=m.period, clock_raw=m.clock_raw,
            )

        # Yellow fly (upcoming prediction)
        if is_yellow and not was_yellow:
            self.db.update_match_flags(conn, match_id, had_yellow_fly=1)
            self.db.log_event(
                conn, match_id=match_id, event_type="yellow_fly",
                match_state=m.status, flytime_score=ft_result.score,
                threshold=ft_result.threshold, formula_version=ft_result.formula_version,
            )
            conn.execute(
                """INSERT INTO fly_events (match_id, fly_type, activated_at, flytime_score,
                   threshold, formula_version) VALUES (?, 'yellow', ?, ?, ?, ?)""",
                (match_id, utcnow(), ft_result.score, ft_result.threshold, ft_result.formula_version),
            )

        # Green fly (live FlyTime)
        if is_green:
            if not was_green:
                self.db.update_match_flags(conn, match_id, had_live_flytime=1)
                self.db.log_event(
                    conn, match_id=match_id, event_type="green_fly",
                    match_state="live", home_score=m.home_score, away_score=m.away_score,
                    period=m.period, clock_raw=m.clock_raw,
                )
                conn.execute(
                    """INSERT INTO fly_events (match_id, fly_type, activated_at, period,
                       clock_raw, margin, time_remaining_sec) VALUES (?, 'green', ?, ?, ?, ?, ?)""",
                    (match_id, utcnow(), m.period, m.clock_raw,
                     abs(m.home_score - m.away_score), m.clock_sec),
                )

            # Blue fly: yellow predicted AND green achieved
            row = conn.execute(
                "SELECT had_yellow_fly FROM matches WHERE id=?", (match_id,)
            ).fetchone()
            if row and row["had_yellow_fly"] and not prev.get("had_blue"):
                self.db.update_match_flags(conn, match_id, had_blue_fly=1)
                self.db.log_event(
                    conn, match_id=match_id, event_type="blue_fly",
                    match_state="live", home_score=m.home_score, away_score=m.away_score,
                    period=m.period, clock_raw=m.clock_raw,
                    flytime_score=ft_result.score, threshold=ft_result.threshold,
                )
                conn.execute(
                    """INSERT INTO blue_fly_events
                       (match_id, league_id, activated_at, yellow_score, yellow_threshold,
                        green_at, match_state_at_activation, period, clock_raw,
                        time_remaining_sec, score_differential, home_score, away_score,
                        formula_version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        match_id, league_id, utcnow(),
                        ft_result.score or 0, ft_result.threshold or 0,
                        utcnow(), "live", m.period, m.clock_raw, m.clock_sec,
                        abs(m.home_score - m.away_score), m.home_score, m.away_score,
                        ft_result.formula_version,
                    ),
                )
                conn.execute(
                    """INSERT INTO fly_events (match_id, fly_type, activated_at, flytime_score,
                       threshold, formula_version, period, clock_raw, margin)
                       VALUES (?, 'blue', ?, ?, ?, ?, ?, ?, ?)""",
                    (match_id, utcnow(), ft_result.score, ft_result.threshold,
                     ft_result.formula_version, m.period, m.clock_raw,
                     abs(m.home_score - m.away_score)),
                )
                prev["had_blue"] = True

        # Red fly on finish
        if m.status == "finished" and prev.get("status") == "live":
            had_live = conn.execute(
                "SELECT had_live_flytime FROM matches WHERE id=?", (match_id,)
            ).fetchone()
            if had_live and had_live["had_live_flytime"]:
                self.db.update_match_flags(conn, match_id, had_red_fly=1)
                self.db.log_event(
                    conn, match_id=match_id, event_type="red_fly",
                    match_state="finished", home_score=m.home_score, away_score=m.away_score,
                )
                conn.execute(
                    """INSERT INTO fly_events (match_id, fly_type, activated_at, margin)
                       VALUES (?, 'red', ?, ?)""",
                    (match_id, utcnow(), abs(m.home_score - m.away_score)),
                )
                conn.execute(
                    "UPDATE blue_fly_events SET became_red_fly=1, final_margin=?, final_winner=? WHERE match_id=?",
                    (
                        abs(m.home_score - m.away_score),
                        "home" if m.home_score > m.away_score else ("away" if m.away_score > m.home_score else "draw"),
                        match_id,
                    ),
                )

        # Live snapshot every poll for live matches
        if m.status == "live":
            self.db.insert_snapshot(
                conn, match_id=match_id, status=m.status,
                period=m.period, clock_raw=m.clock_raw, clock_sec=m.clock_sec,
                home_score=m.home_score, away_score=m.away_score,
                is_flytime=is_green, flytime_score=ft_result.score,
                threshold=ft_result.threshold, formula_version=ft_result.formula_version,
                is_yellow=is_yellow, is_blue=prev.get("had_blue", False),
                is_red=False, is_flymode=is_green,
            )

        self._record_prediction(conn, match_id, league, m, actual_fly=is_green or (
            m.status == "finished" and retroactive_flytime_from_final(
                m.home_score, m.away_score, league.close_margin
            )
        ))

        self._live_state[match_id] = {
            "status": m.status,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "had_yellow": was_yellow or is_yellow or prev.get("had_yellow", False),
            "had_green": was_green or is_green or prev.get("had_green", False),
            "had_blue": prev.get("had_blue", False),
        }

    def _record_prediction(
        self,
        conn,
        match_id: int,
        league: LeagueConfig,
        m: ParsedMatch,
        actual_fly: bool,
    ) -> None:
        for fv in ("v1", "v2", "v3", "experimental"):
            result = self.engine.score_for_league(m, league, formula_version=fv)
            if result.score is None:
                continue
            predicted = result.is_yellow
            conn.execute(
                """INSERT OR REPLACE INTO prediction_results
                   (match_id, formula_version, threshold, flytime_score, predicted_fly,
                    actual_fly, is_hit, is_false_alarm, is_miss, scored_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    match_id, fv, result.threshold, result.score, int(predicted),
                    int(actual_fly), int(predicted and actual_fly),
                    int(predicted and not actual_fly), int(not predicted and actual_fly),
                    utcnow(),
                ),
            )


class CollectionService:
    """Always-on polling service with adaptive intervals."""

    def __init__(self, db: Database):
        self.db = db
        self.engine = FlyTimeEngine()
        self.engine.load_all(LEAGUES)
        self.collector = MatchCollector(db, self.engine)
        self._fast_cycles = 0
        self._running = False

    def start(self) -> None:
        self._running = True
        self.db.set_service_state("service_status", "running")
        self.db.set_service_state("service_started_at", utcnow())
        print("FlyTime Data Engine started.", flush=True)

        while self._running:
            try:
                self.collector.poll_all()
                self._fast_cycles += 1

                any_flytime = self.db.get_service_state("any_live_flytime") == "1"
                if any_flytime:
                    interval = POLL_FLYTIME_SEC
                elif self._fast_cycles < POLL_FULL_SWEEP_EVERY:
                    interval = POLL_FAST_SEC
                else:
                    self._fast_cycles = 0
                    interval = POLL_IDLE_SEC

                self.db.set_service_state("next_poll_interval", str(interval))
                time.sleep(interval)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"Poll cycle error: {e}", flush=True)
                self.db.set_service_state("last_error", str(e))
                time.sleep(POLL_IDLE_SEC)

    def stop(self) -> None:
        self._running = False
        self.db.set_service_state("service_status", "stopped")
        print("FlyTime Data Engine stopped.", flush=True)
