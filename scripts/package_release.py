"""Put the attested exe and a zip with the readme under dist/."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE_NAMES = ("立体声修复.exe", "TabStereoFix.exe")


def _find_exe(out_dir: Path) -> Path | None:
    for name in EXE_NAMES:
        path = out_dir / name
        if path.is_file():
            return path
    return None


def main() -> None:
    version = os.environ.get("GITHUB_REF_NAME") or "local"
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    exe = _find_exe(out_dir)
    if exe is None:
        raise SystemExit("missing dist/立体声修复.exe — run scripts/build_exe.py first")
    zip_path = out_dir / f"tab-stereo-fix-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(exe, "立体声修复.exe")
        readme = ROOT / "安装说明.txt"
        if readme.is_file():
            archive.write(readme, "安装说明.txt")
    print(exe.exists(), exe.name.encode("unicode_escape").decode())
    print(zip_path.name)


if __name__ == "__main__":
    main()
