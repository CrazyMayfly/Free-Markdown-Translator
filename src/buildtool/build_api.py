"""Build the mdtx-api sidecar binary for the Tauri shell.

Usage (from repo root):
    .venv/bin/python src/buildtool/build_api.py

Produces ui/src-tauri/binaries/mdtx-api-<target-triple>[.exe] — the layout
Tauri's externalBin expects ("binaries/mdtx-api" in tauri.conf.json).
"""

from __future__ import annotations

import platform
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def target_triple() -> str:
    system = platform.system().lower()
    # platform.machine() is "AMD64" on Windows and "arm64" on macOS; compare
    # lowercased and normalize to Rust's triple naming (x86_64, aarch64).
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "aarch64"
    else:
        arch = machine
    if system == "darwin":
        return f"{arch}-apple-darwin"
    if system == "windows":
        return f"{arch}-pc-windows-msvc"
    return f"{arch}-unknown-linux-gnu"


# uvicorn lazy-imports these; PyInstaller cannot see them statically.
UVICORN_HIDDEN = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]


def build() -> Path:
    triple = target_triple()
    output_dir = REPO_ROOT / "ui" / "src-tauri" / "binaries"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if triple.endswith("windows-msvc") else ""
    final_name = output_dir / f"mdtx-api-{triple}{suffix}"

    with tempfile.TemporaryDirectory() as work_dir:
        spec_args = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--name",
            f"mdtx-api-{triple}",
            "--distpath",
            str(output_dir),
            "--workpath",
            str(Path(work_dir) / "build"),
            "--specpath",
            str(work_dir),
            "--paths",
            str(REPO_ROOT),
            *[f"--hidden-import={module}" for module in UVICORN_HIDDEN],
            str(REPO_ROOT / "src" / "api" / "__main__.py"),
        ]
        subprocess.run(spec_args, check=True, cwd=str(REPO_ROOT))

    binary = output_dir / f"mdtx-api-{triple}{suffix}"
    if not binary.exists():
        raise SystemExit(f"PyInstaller did not produce {binary}")
    # Tauri expects the bare-triple name without an extra suffix on unix.
    binary.chmod(0o755)
    print(f"Sidecar ready: {final_name} ({binary.stat().st_size / 1e6:.1f} MB)")
    return binary


if __name__ == "__main__":
    build()
