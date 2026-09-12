"""Create the attested zip under dist/."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"__pycache__", ".git", "config", "dist", ".github"}
INCLUDE = [
    "desktop",
    "extension",
    "scripts",
    "启动立体声修复.bat",
    "一键关闭 Wide AEC.bat",
    "run-app.bat",
    "安装开关.bat",
    "README.md",
    "安装说明.txt",
]


def main() -> None:
    version = os.environ.get("GITHUB_REF_NAME") or "local"
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    zip_path = out_dir / f"tab-stereo-fix-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in INCLUDE:
            path = ROOT / name
            if path.is_file():
                archive.write(path, name)
                continue
            if not path.is_dir():
                continue
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue
                if any(part in SKIP for part in file_path.parts):
                    continue
                archive.write(file_path, file_path.relative_to(ROOT).as_posix())
    print(zip_path)


if __name__ == "__main__":
    main()
