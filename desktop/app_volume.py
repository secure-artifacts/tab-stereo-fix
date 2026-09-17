"""Raise only the selected browser install's session volume. 0.0-1.0 only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BROWSER_EXES = {"chrome.exe", "msedge.exe", "brave.exe", "chromium.exe", "vivaldi.exe"}


def _norm_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(str(path).strip().strip('"')))


def _product_key(path) -> str:
    lower = _norm_path(path).replace("/", "\\").lower()
    rules = (
        ("chrome protect", "chrome-protect"),
        ("chromeprotect", "chrome-protect"),
        ("chrome for testing", "chrome-testing"),
        ("chrome sxs", "chrome-canary"),
        ("chrome canary", "chrome-canary"),
        ("chrome dev", "chrome-dev"),
        ("chrome beta", "chrome-beta"),
        ("vivaldi snapshot", "vivaldi-snapshot"),
        ("vivaldi", "vivaldi"),
        ("edge sxs", "edge-canary"),
        ("edge canary", "edge-canary"),
        ("edge dev", "edge-dev"),
        ("edge beta", "edge-beta"),
        ("bravesoftware", "brave"),
        ("\\brave-browser\\", "brave"),
        ("\\chromium\\", "chromium"),
    )
    for needle, key in rules:
        if needle in lower:
            return key
    if "bravesoftware" in lower or "\\brave" in lower:
        return "brave"
    if "\\microsoft\\edge" in lower or "\\edge\\" in lower:
        return "edge"
    if "\\google\\chrome" in lower or "\\chrome\\" in lower:
        return "chrome"
    return Path(lower).name.lower()


def _path_allowed(path: str, allowed_paths: set[str]) -> bool:
    norm = _norm_path(path)
    if norm in allowed_paths:
        return True
    key = _product_key(path)
    return any(_product_key(item) == key for item in allowed_paths)


def set_browser_volume(
    level: float,
    exe_paths: set[str] | None = None,
    exe_names: set[str] | None = None,
) -> int:
    allowed_paths = {_norm_path(path) for path in (exe_paths or set()) if path}
    if not allowed_paths:
        return 0
    allowed_names = {name.lower() for name in (exe_names or set()) if name}
    value = max(0.0, min(1.0, float(level)))
    try:
        if getattr(sys, "frozen", False) or globals().get("__compiled__"):
            gen = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "TabStereoFix" / "comtypes-gen"
            gen.mkdir(parents=True, exist_ok=True)
            import comtypes.client

            comtypes.client.gen_dir = str(gen)
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    except ImportError:
        return 0
    changed = 0
    for session in AudioUtilities.GetAllSessions():
        process = session.Process
        if not process:
            continue
        try:
            name = (process.name() or "").lower()
            path = process.exe() or ""
        except Exception:
            continue
        if name not in BROWSER_EXES:
            continue
        if allowed_names and name not in allowed_names:
            continue
        if not path or not _path_allowed(path, allowed_paths):
            continue
        try:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            volume.SetMasterVolume(value, None)
            volume.SetMute(0, None)
            changed += 1
        except Exception:
            continue
    return changed
