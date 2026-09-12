"""Build a one-file Windows exe that others can download and open."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "立体声修复"


def main() -> None:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        EXE_NAME,
        "--paths",
        str(ROOT),
        "--distpath",
        str(dist),
        "--workpath",
        str(ROOT / "build" / "pyinstaller"),
        "--specpath",
        str(ROOT / "build"),
        "--hidden-import",
        "desktop.app",
        "--hidden-import",
        "desktop.app_volume",
        "--hidden-import",
        "desktop.autostart",
        "--hidden-import",
        "desktop.browser_audio_fix",
        "--hidden-import",
        "desktop.paths",
        "--hidden-import",
        "pycaw.pycaw",
        "--hidden-import",
        "comtypes",
        "--hidden-import",
        "comtypes.stream",
        str(ROOT / "desktop" / "app.py"),
    ]
    subprocess.check_call(command)
    exe = dist / f"{EXE_NAME}.exe"
    if not exe.is_file():
        raise SystemExit("missing dist exe")
    print(exe.exists(), exe.name.encode("unicode_escape").decode())


if __name__ == "__main__":
    main()
