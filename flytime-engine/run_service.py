#!/usr/bin/env python3
"""Entry point for always-on FlyTime Data Engine service."""
from __future__ import annotations

import atexit
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from flytime_engine.collector import CollectionService
from flytime_engine.config import DEFAULT_DB_PATH
from flytime_engine.db import Database

ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / "data" / "monitor.pid"
LOG_FILE = ROOT / "logs" / "monitor.log"


def _log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}\n"
    LOG_FILE.open("a", encoding="utf-8").write(line)
    print(msg, flush=True)


def _write_pid() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid() -> None:
    PID_FILE.unlink(missing_ok=True)


def main():
    _write_pid()
    atexit.register(_remove_pid)
    _log("FlyTime live monitor started.")
    try:
        db = Database(DEFAULT_DB_PATH)
        db.init_schema()
        service = CollectionService(db)
        service.start()
    except KeyboardInterrupt:
        _log("Stopped by user.")
    except Exception as e:
        _log(f"ERROR: {e}")
        raise
    finally:
        _remove_pid()
        _log("FlyTime live monitor stopped.")


if __name__ == "__main__":
    main()
