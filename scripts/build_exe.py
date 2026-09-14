"""Build a Windows folder app. Avoid one-file packing so antivirus is less likely to flag it."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "TabStereoFix"
ICON = ROOT / "desktop" / "assets" / "app.ico"
ASSETS = ROOT / "desktop" / "assets"


def release_version() -> str:
    raw = (os.environ.get("GITHUB_REF_NAME") or "1.5.1").lstrip("v")
    parts = [item if item.isdigit() else "0" for item in raw.split(".")]
    while len(parts) < 4:
        parts.append("0")
    return ".".join(parts[:4])


def write_version_file(path: Path) -> str:
    version = release_version()
    nums = ", ".join(version.split("."))
    path.write_text(
        "\n".join(
            [
                "VSVersionInfo(",
                "  ffi=FixedFileInfo(",
                f"    filevers=({nums}),",
                f"    prodvers=({nums}),",
                "    mask=0x3F,",
                "    flags=0x0,",
                "    OS=0x40004,",
                "    fileType=0x1,",
                "    subtype=0x0,",
                "    date=(0, 0)",
                "  ),",
                "  kids=[",
                "    StringFileInfo([",
                "      StringTable(",
                "        '040904B0',",
                "        [",
                "          StringStruct('CompanyName', 'MELO MZ'),",
                "          StringStruct('FileDescription', 'TabStereoFix browser audio helper'),",
                f"          StringStruct('FileVersion', '{version}'),",
                "          StringStruct('InternalName', 'TabStereoFix'),",
                "          StringStruct('LegalCopyright', 'Copyright (C) MELO MZ'),",
                "          StringStruct('OriginalFilename', 'TabStereoFix.exe'),",
                "          StringStruct('ProductName', 'TabStereoFix'),",
                f"          StringStruct('ProductVersion', '{version}'),",
                "        ],",
                "      )",
                "    ]),",
                "    VarFileInfo([VarStruct('Translation', [1033, 1200])])",
                "  ]",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return version


def main() -> None:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    version_file = ROOT / "build" / "file_version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    write_version_file(version_file)
    sep = ";" if os.name == "nt" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--noupx",
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
        "--version-file",
        str(version_file),
        "--add-data",
        f"{ASSETS}{sep}desktop/assets",
        "--exclude-module",
        "numpy.libs",
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
        "desktop.categories",
        "--hidden-import",
        "desktop.i18n",
        "--hidden-import",
        "pycaw.pycaw",
        "--hidden-import",
        "comtypes",
        "--hidden-import",
        "comtypes.stream",
    ]
    if ICON.is_file():
        command.extend(["--icon", str(ICON)])
    command.append(str(ROOT / "desktop" / "app.py"))
    subprocess.check_call(command)
    exe = dist / EXE_NAME / f"{EXE_NAME}.exe"
    if not exe.is_file():
        raise SystemExit("missing dist/TabStereoFix/TabStereoFix.exe")
    starter = exe.with_name("打开立体声修复.bat")
    starter.write_text(
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        'start "" "%~dp0TabStereoFix.exe"\r\n',
        encoding="utf-8",
    )
    readme = ROOT / "安装说明.txt"
    if readme.is_file():
        (exe.parent / "安装说明.txt").write_bytes(readme.read_bytes())
    print("ok", exe.exists())


if __name__ == "__main__":
    main()
