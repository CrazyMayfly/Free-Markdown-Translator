"""Entry point for the PyInstaller-built mdtx-api sidecar.

The Tauri shell spawns `mdtx-api --port <N> [--parent-pid <pid>]`; the port
is chosen by the shell and never opened in a browser. With --parent-pid the
sidecar watches its parent and exits when the shell dies, so no orphaned
server processes can outlive the desktop app.
"""

from __future__ import annotations

import argparse
import os
import threading
import time


def _watch_parent(parent_pid: int) -> None:
    # Poll the shell PID directly (not os.getppid): the PyInstaller onefile
    # bootloader sits between us and the shell, so a re-parented grandchild
    # would never see its own ppid change.
    while True:
        time.sleep(2)
        try:
            os.kill(parent_pid, 0)
        except ProcessLookupError:
            os._exit(0)
        except PermissionError:  # exists but not ours — still alive
            continue


def main() -> None:
    parser = argparse.ArgumentParser(prog="mdtx-api", description="mdtx UI API server (sidecar).")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on (127.0.0.1 only).")
    parser.add_argument("--parent-pid", type=int, default=None, help="Exit automatically when this process dies.")
    args = parser.parse_args()

    if args.parent_pid:
        watcher = threading.Thread(target=_watch_parent, args=(args.parent_pid,), daemon=True)
        watcher.start()

    import uvicorn

    from src.api.app import create_app
    from src.api.history import JobHistory

    uvicorn.run(
        create_app(history=JobHistory()),
        host="127.0.0.1",
        port=args.port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
