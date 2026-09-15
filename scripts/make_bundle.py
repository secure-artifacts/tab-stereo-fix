"""Build a portable folder that runs on official signed CPython.

PyInstaller bootloaders are frequently flagged as viruses. This copies
pythonw.exe from the Python.org runtime (Authenticode signed) and launches
the Tk app through sitecustomize when TabStereoFix.exe is opened with no
arguments.
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
SKIP_LIB = {
    "__pycache__",
    "ensurepip",
    "idlelib",
    "site-packages",
    "test",
    "turtledemo",
}


def release_version() -> str:
    raw = (os.environ.get("GITHUB_REF_NAME") or "1.6.0").lstrip("v")
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


def _ignore_lib(directory: str, names: list[str]) -> list[str]:
    dropped = [name for name in names if name in SKIP_LIB or name.endswith(".pyc")]
    if Path(directory).name == "tkinter" and "test" in names:
        dropped.append("test")
    return dropped


def _copy_runtime(prefix: Path, dest: Path) -> None:
    abi = f"python{sys.version_info.major}{sys.version_info.minor}"
    for name in ("python.exe", "pythonw.exe", "python3.dll", f"{abi}.dll"):
        src = prefix / name
        if src.is_file():
            shutil.copy2(src, dest / name)
    for pattern in ("vcruntime*.dll", "concrt*.dll", "msvcp*.dll"):
        for src in prefix.glob(pattern):
            shutil.copy2(src, dest / src.name)
    for folder in ("DLLs", "tcl"):
        src = prefix / folder
        if src.is_dir():
            shutil.copytree(src, dest / folder, dirs_exist_ok=True)
    lib = prefix / "Lib"
    if not lib.is_dir():
        raise SystemExit(f"missing Python Lib at {lib}")
    shutil.copytree(lib, dest / "Lib", ignore=_ignore_lib, dirs_exist_ok=True)
    (dest / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def _write_sitecustomize(dest: Path) -> None:
    path = dest / "Lib" / "sitecustomize.py"
    path.write_text(
        "import sys\n"
        "\n"
        "def _should_start_app() -> bool:\n"
        "    if len(sys.argv) > 1:\n"
        "        return False\n"
        "    name = sys.argv[0].replace('\\\\', '/').rsplit('/', 1)[-1].lower()\n"
        "    return name in {'tabstereofix.exe', 'pythonw.exe'}\n"
        "\n"
        "if _should_start_app():\n"
        "    import runpy\n"
        "    runpy.run_module('desktop.app', run_name='__main__')\n",
        encoding="utf-8",
    )
    if not path.is_file():
        raise SystemExit("failed to write sitecustomize.py")


def main() -> None:
    dest = DEST_DIR
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "make_icons.py")])
    if not ICON.is_file():
        raise SystemExit("missing desktop/assets/app.ico after make_icons")
    prefix = Path(sys.base_prefix)
    _copy_runtime(prefix, dest)
    pythonw = dest / "pythonw.exe"
    if not pythonw.is_file():
        raise SystemExit(f"missing pythonw.exe in {prefix}")
    shutil.copy2(pythonw, dest / f"{EXE_NAME}.exe")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--target",
            str(dest / "Lib" / "site-packages"),
            "pycaw",
            "comtypes",
        ]
    )
    shutil.copytree(
        ROOT / "desktop",
        dest / "Lib" / "site-packages" / "desktop",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "check_app.py", "test_fix.py", "gain_ext"),
        dirs_exist_ok=True,
    )
    app_py = dest / "Lib" / "site-packages" / "desktop" / "app.py"
    if not app_py.is_file():
        raise SystemExit("desktop app.py was not copied into the package")
    _write_sitecustomize(dest)
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
    exe = dest / f"{EXE_NAME}.exe"
    if not exe.is_file():
        raise SystemExit("missing release/TabStereoFix/TabStereoFix.exe")
    print("ok", exe, "signed-python-runtime")


if __name__ == "__main__":
    main()
