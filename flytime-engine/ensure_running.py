"""Start the platform only if not already listening on port 8787."""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

PORT = 8787
ROOT = Path(__file__).resolve().parent


def is_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=1):
            return True
    except OSError:
        return False


def main() -> None:
    if is_running():
        return
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    subprocess.Popen(
        [sys.executable, str(ROOT / "run_platform.py")],
        cwd=str(ROOT),
        creationflags=flags,
    )


if __name__ == "__main__":
    main()
