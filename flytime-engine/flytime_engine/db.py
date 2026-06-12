"""Database layer with schema init and common operations."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from .config import DEFAULT_DB_PATH, FORMULA_VERSIONS, LEAGUES


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    def __init__(self, path: Path = DEFAULT_DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        schema_path = Path(__file__).resolve().parent.parent / "schema.sql"
        sql = schema_path.read_text(encoding="utf-8")
        with self.session() as conn:
            conn.executescript(sql)
            self._seed_reference_data(conn)

    def _seed_reference_data(self, conn: sqlite3.Connection) -> None:
        for key, fv in FORMULA_VERSIONS.items():
            conn.execute(
                """INSERT OR IGNORE INTO formula_versions
                   (version_key, name, weights_json, is_production)
                   VALUES (?, ?, ?, ?)""",
                (key, fv["name"], json.dumps(fv["weights"]), int(fv["is_production"])),
            )
        for lg in LEAGUES:
            conn.execute(
                """INSERT OR IGNORE INTO leagues
                   (sport, league_code, label, tag, flytime_file, close_margin,
                    chunk_size, threshold, threshold_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'fixed')""",
                (
                    lg.sport, lg.league_code, lg.label, lg.tag, lg.flytime_file,
                    lg.close_margin, lg.chunk_size, lg.threshold,
                ),
            )

    def get_league_id(self, conn: sqlite3.Connection, sport: str, league_code: str) -> Optional[int]:
        row = conn.execute(
            "SELECT id FROM leagues WHERE sport=? AND league_code=?",
            (sport, league_code),
        ).fetchone()
        return row["id"] if row else None

    def get_service_state(self, key: str) -> Optional[str]:
        with self.session() as conn:
            row = conn.execute(
                "SELECT value FROM service_state WHERE key=?", (key,)
            ).fetchone()
            return row["value"] if row else None

    def set_service_state(self, key: str, value: str) -> None:
        with self.session() as conn:
            conn.execute(
                """INSERT INTO service_state (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (key, value, utcnow()),
            )

    def upsert_match(
        self,
        conn: sqlite3.Connection,
        *,
        espn_event_id: str,
        league_id: int,
        home_team: str,
        away_team: str,
        scheduled_at: Optional[str],
        status: str,
        home_score: Optional[int] = None,
        away_score: Optional[int] = None,
        season: Optional[str] = None,
        venue: Optional[str] = None,
        home_team_id: Optional[str] = None,
        away_team_id: Optional[str] = None,
    ) -> int:
        now = utcnow()
        margin = None
        if home_score is not None and away_score is not None:
            margin = abs(home_score - away_score)

        row = conn.execute(
            "SELECT id, status, had_live_flytime, had_yellow_fly FROM matches WHERE espn_event_id=?",
            (espn_event_id,),
        ).fetchone()

        if row:
            finished_at = now if status == "finished" and row["status"] != "finished" else None
            conn.execute(
                """UPDATE matches SET
                   home_team=?, away_team=?, scheduled_at=?, status=?,
                   home_score=?, away_score=?, final_margin=?, season=?, venue=?,
                   home_team_id=?, away_team_id=?,
                   last_polled_at=?, finished_at=COALESCE(?, finished_at), updated_at=?
                   WHERE id=?""",
                (
                    home_team, away_team, scheduled_at, status,
                    home_score, away_score, margin, season, venue,
                    home_team_id, away_team_id, now, finished_at, now, row["id"],
                ),
            )
            return row["id"]

        conn.execute(
            """INSERT INTO matches
               (espn_event_id, league_id, home_team, away_team, home_team_id, away_team_id,
                venue, scheduled_at, status, home_score, away_score, final_margin, season,
                first_seen_at, last_polled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                espn_event_id, league_id, home_team, away_team, home_team_id, away_team_id,
                venue, scheduled_at, status, home_score, away_score, margin, season,
                now, now,
            ),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def log_event(
        self,
        conn: sqlite3.Connection,
        *,
        match_id: int,
        event_type: str,
        match_state: Optional[str] = None,
        home_score: Optional[int] = None,
        away_score: Optional[int] = None,
        period: Optional[int] = None,
        clock_raw: Optional[str] = None,
        flytime_score: Optional[float] = None,
        threshold: Optional[float] = None,
        formula_version: str = "v1",
        detail: Optional[dict] = None,
    ) -> None:
        conn.execute(
            """INSERT INTO match_events
               (match_id, event_at, event_type, match_state, home_score, away_score,
                period, clock_raw, flytime_score, threshold, formula_version, detail_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id, utcnow(), event_type, match_state, home_score, away_score,
                period, clock_raw, flytime_score, threshold, formula_version,
                json.dumps(detail) if detail else None,
            ),
        )

    def insert_snapshot(
        self,
        conn: sqlite3.Connection,
        *,
        match_id: int,
        status: str,
        period: int,
        clock_raw: str,
        clock_sec: int,
        home_score: int,
        away_score: int,
        is_flytime: bool,
        flytime_score: Optional[float],
        threshold: Optional[float],
        formula_version: str,
        is_yellow: bool = False,
        is_blue: bool = False,
        is_red: bool = False,
        is_flymode: bool = False,
        extra: Optional[dict] = None,
    ) -> None:
        conn.execute(
            """INSERT INTO live_snapshots
               (match_id, captured_at, status, period, clock_raw, clock_sec,
                home_score, away_score, margin, is_flytime, flytime_score, threshold,
                formula_version, is_yellow, is_blue, is_red, is_flymode, extra_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id, utcnow(), status, period, clock_raw, clock_sec,
                home_score, away_score, abs(home_score - away_score),
                int(is_flytime), flytime_score, threshold, formula_version,
                int(is_yellow), int(is_blue), int(is_red), int(is_flymode),
                json.dumps(extra) if extra else None,
            ),
        )

    def update_match_flags(
        self,
        conn: sqlite3.Connection,
        match_id: int,
        **flags: Any,
    ) -> None:
        allowed = {"had_live_flytime", "had_yellow_fly", "had_blue_fly", "had_red_fly"}
        sets = []
        vals = []
        for k, v in flags.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(int(v))
        if not sets:
            return
        vals.append(match_id)
        conn.execute(f"UPDATE matches SET {', '.join(sets)}, updated_at=? WHERE id=?",
                     vals[:-1] + [utcnow(), match_id])

    def query_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.session() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with self.session() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
