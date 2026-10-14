from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infra.config import render_default_config_yaml

BUILD_ROOT = Path(__file__).resolve().parent
OUT_DIR = BUILD_ROOT / "out"
WORK_DIR = BUILD_ROOT / "work"
SPEC_DIR = BUILD_ROOT / "spec"
ENTRYPOINT = PROJECT_ROOT / "src" / "cli" / "main.py"
EXE_NAME = "mdtx"
UPX_EXE = BUILD_ROOT / "upx.exe"
ICON_PNG = BUILD_ROOT / "icon.png"
ICON_ICO = BUILD_ROOT / "icon.ico"


def _prepare_icon() -> Path | None:
    if not ICON_PNG.exists():
        return None

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Detected src/buildtool/icon.png, but Pillow is not installed. "
            "Run `pip install -r src/buildtool/requirements-build.txt` first."
        ) from exc

    if ICON_ICO.exists() and ICON_ICO.stat().st_mtime >= ICON_PNG.stat().st_mtime:
        return ICON_ICO

    with Image.open(ICON_PNG) as image:
        rgba_image = image.convert("RGBA")
        rgba_image.save(
            ICON_ICO,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    return ICON_ICO


def _run_pyinstaller() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        EXE_NAME,
        "--distpath",
        str(OUT_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--paths",
        str(PROJECT_ROOT),
        "--collect-submodules",
        "openai",
        "--collect-submodules",
        "markdown_it",
        "--hidden-import",
        "tqdm",
        "--hidden-import",
        "yaml",
    ]

    if UPX_EXE.exists():
        command.extend(["--upx-dir", str(BUILD_ROOT)])

    icon_path = _prepare_icon()
    if icon_path is not None:
        command.extend(["--icon", str(icon_path)])

    command.append(str(ENTRYPOINT))
    completed = subprocess.run(command, cwd=PROJECT_ROOT)
    return completed.returncode


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print(
            "PyInstaller is not installed. Run `pip install -r src/buildtool/requirements-build.txt` first.",
            file=sys.stderr,
        )
        return 1

    try:
        exit_code = _run_pyinstaller()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if exit_code != 0:
        return exit_code

    config_template = OUT_DIR / "config.template.yaml"
    config_template.write_text(render_default_config_yaml(), encoding="utf-8")

    if UPX_EXE.exists():
        print(f"UPX enabled: {UPX_EXE}")
    else:
        print("UPX skipped: src/buildtool/upx.exe not found")

    if ICON_PNG.exists():
        print(f"Icon enabled: {ICON_ICO}")
    else:
        print("Icon skipped: src/buildtool/icon.png not found")

    print(f"Build finished: {OUT_DIR / (EXE_NAME + '.exe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
