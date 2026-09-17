"""Writable paths for source runs and the shipped folder app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PORTABLE_MARK = "TabStereoFix.portable"


def is_frozen() -> bool:
    if bool(getattr(sys, "frozen", False)):
        return True
    if globals().get("__compiled__"):
        return True
    return (Path(sys.executable).resolve().parent / PORTABLE_MARK).is_file()


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def config_dir() -> Path:
    if is_frozen():
        return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "TabStereoFix"
    return app_root() / "config"


def config_file(name: str) -> Path:
    return config_dir() / name


def launcher_dir() -> Path:
    if is_frozen():
        return config_dir() / "launchers"
    return app_root() / "launchers"


def asset_file(name: str) -> Path:
    here = Path(__file__).resolve().parent.parent / "assets" / name
    if here.is_file():
        return here
    if is_frozen():
        meipass = Path(getattr(sys, "_MEIPASS", app_root()))
        for candidate in (
            meipass / "desktop" / "assets" / name,
            meipass / "assets" / name,
            app_root() / "desktop" / "assets" / name,
        ):
            if candidate.is_file():
                return candidate
    return here
