"""Zip the folder app. Only ASCII names go to GitHub, so it is not renamed to default.exe."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "dist" / "TabStereoFix"
EXE_NAME = "TabStereoFix.exe"


def main() -> None:
    version = os.environ.get("GITHUB_REF_NAME") or "local"
    exe = APP_DIR / EXE_NAME
    if not exe.is_file():
        raise SystemExit("missing dist/TabStereoFix/TabStereoFix.exe — run scripts/build_exe.py first")
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    zip_path = out_dir / f"TabStereoFix-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in APP_DIR.rglob("*"):
            if not file_path.is_file():
                continue
            archive.write(file_path, Path("TabStereoFix") / file_path.relative_to(APP_DIR))
    print(zip_path.name)


if __name__ == "__main__":
    main()
