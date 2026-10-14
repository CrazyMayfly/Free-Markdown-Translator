"""Entry point for the PyInstaller-built mdtx-api sidecar.

The Tauri shell spawns `mdtx-api --port <N>`; the port is chosen by the
shell and never opened in a browser.
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="mdtx-api", description="mdtx UI API server (sidecar).")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on (127.0.0.1 only).")
    args = parser.parse_args()

    import uvicorn

    from src.api.app import create_app

    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
