"""Build a standalone Windows folder app with Nuitka.

Users do not install Python. The zip contains TabStereoFix.exe plus its
runtime files. Nuitka compiles to a real program instead of a PyInstaller
bootloader, which antivirus often flags.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "TabStereoFix"
DEST_DIR = ROOT / "release" / EXE_NAME
ICON = ROOT / "desktop" / "assets" / "app.ico"


def release_version() -> str:
    raw = (os.environ.get("GITHUB_REF_NAME") or "1.8.0").lstrip("v")
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


def _nuitka_command(out: Path) -> list[str]:
    version = release_version()
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={ICON}",
        "--windows-company-name=MELO MZ",
        "--windows-product-name=TabStereoFix",
        "--windows-file-description=TabStereoFix browser audio helper",
        f"--windows-file-version={version}",
        f"--windows-product-version={version}",
        "--include-package=desktop",
        "--include-package=pycaw",
        "--include-package=comtypes",
        "--include-package=psutil",
        "--include-data-dir=desktop/assets=desktop/assets",
        "--output-filename=TabStereoFix.exe",
        f"--output-dir={out}",
        str(ROOT / "desktop" / "app.py"),
    ]
    if os.environ.get("GITHUB_ACTIONS"):
        command.insert(5, "--msvc=latest")
    else:
        command.insert(5, "--mingw64")
    return command


def main() -> None:
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "make_icons.py")])
    if not ICON.is_file():
        raise SystemExit("missing desktop/assets/app.ico after make_icons")
    out = ROOT / "build" / "nuitka"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(_nuitka_command(out), cwd=str(ROOT), env=env)
    dist_dirs = [path for path in out.glob("*.dist") if path.is_dir()]
    if not dist_dirs:
        raise SystemExit("Nuitka did not produce a .dist folder")
    dest = DEST_DIR
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(dist_dirs[0], dest)
    exe = dest / f"{EXE_NAME}.exe"
    if not exe.is_file():
        found = list(dest.glob("*.exe"))
        raise SystemExit(f"missing TabStereoFix.exe in {dest}, have {found}")
    (dest / "TabStereoFix.portable").write_text(release_version(), encoding="utf-8")
    (dest / "打开立体声修复.bat").write_text(
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        'start "" "%~dp0TabStereoFix.exe"\r\n',
        encoding="utf-8",
    )
    readme = ROOT / "安装说明.txt"
    if readme.is_file():
        (dest / "安装说明.txt").write_bytes(readme.read_bytes())
    print("ok", exe)


if __name__ == "__main__":
    main()
