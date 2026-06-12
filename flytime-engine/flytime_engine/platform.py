"""Fly Intelligence Platform — cloud runner combining collector + dashboard."""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .analytics import Analytics
from .collector import CollectionService
from .config import DEFAULT_DB_PATH
from .db import Database, utcnow
from .dashboard import run_dashboard


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)


class FlyIntelligencePlatform:
    """24/7 cloud platform: live collection, nightly analysis, web dashboard."""

    NIGHTLY_HOUR_UTC = 3  # Run analyze + feature export at 03:00 UTC

    def __init__(
        self,
        db: Database,
        host: str = "0.0.0.0",
        port: int = 8787,
        enable_nightly: bool = True,
    ):
        self.db = db
        self.host = host
        self.port = port
        self.enable_nightly = enable_nightly
        self._collector = CollectionService(db)
        self._stop = threading.Event()
        self._last_nightly_date: str | None = None

    def _collector_loop(self) -> None:
        _log("Collector thread started.")
        self._collector.start()

    def _nightly_loop(self) -> None:
        if not self.enable_nightly:
            return
        _log("Nightly analysis scheduler started.")
        while not self._stop.is_set():
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            if now.hour == self.NIGHTLY_HOUR_UTC and self._last_nightly_date != today:
                self._run_nightly_jobs()
                self._last_nightly_date = today
            self._stop.wait(300)  # check every 5 minutes

    def _run_nightly_jobs(self) -> None:
        _log("Running nightly analysis...")
        try:
            from .threshold_engine import ThresholdEngine
            from .formula_testing import FormulaTester
            from .flytime import FlyTimeEngine
            from .config import LEAGUES

            engine = FlyTimeEngine()
            engine.load_all(LEAGUES)
            ThresholdEngine(self.db, engine).evaluate_all()
            FormulaTester(self.db, engine).rank_formulas()
            self.db.set_service_state("last_nightly_at", utcnow())
            _log("Nightly threshold + formula analysis complete.")

            try:
                import sys
                fb_path = Path(__file__).resolve().parent.parent / "feature_builder.py"
                if fb_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("feature_builder", fb_path)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        features = mod.build_features(self.db)
                        out_dir = Path(os.environ.get(
                            "FEATURE_EXPORT_DIR",
                            str(Path(__file__).resolve().parent.parent / "exports"),
                        ))
                        mod.export_csv(features, out_dir / f"{utcnow()[:10]}.csv")
                        _log(f"Feature export: {len(features)} rows → {out_dir}")
            except Exception as e:
                _log(f"Feature export skipped: {e}")

        except Exception as e:
            _log(f"Nightly analysis error: {e}")
            self.db.set_service_state("last_nightly_error", str(e))

    def start(self) -> None:
        self.db.init_schema()
        self.db.set_service_state("platform_mode", "cloud")
        self.db.set_service_state("platform_started_at", utcnow())

        collector_thread = threading.Thread(
            target=self._collector_loop, name="fly-collector", daemon=True
        )
        nightly_thread = threading.Thread(
            target=self._nightly_loop, name="fly-nightly", daemon=True
        )

        collector_thread.start()
        nightly_thread.start()

        _log(f"Fly Intelligence Platform starting on {self.host}:{self.port}")
        run_dashboard(self.db, host=self.host, port=self.port)

    def stop(self) -> None:
        self._stop.set()
        self._collector.stop()


def run_platform(
    db_path: Path | None = None,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Entry point for cloud deployment."""
    path = db_path or Path(os.environ.get("FLYTIME_DB_PATH", str(DEFAULT_DB_PATH)))
    h = host or os.environ.get("HOST", "0.0.0.0")
    p = port or int(os.environ.get("PORT", "8787"))

    db = Database(path)
    platform = FlyIntelligencePlatform(db, host=h, port=p)
    try:
        platform.start()
    except KeyboardInterrupt:
        platform.stop()
