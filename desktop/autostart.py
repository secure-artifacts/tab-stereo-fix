"""Toggle Windows logon start for this app only. Does not open any browser."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_NAME = "TabStereoFix"
VBS_PATH = ROOT / "config" / "autostart.vbs"
START_BAT = ROOT / "启动立体声修复.bat"


def _wscript() -> Path:
    root = os.environ.get("SystemRoot") or r"C:\Windows"
    return Path(root) / "System32" / "wscript.exe"


def autostart_command() -> str:
    return f'"{_wscript()}" //nologo "{VBS_PATH}"'


def write_autostart_vbs() -> Path:
    VBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "Set sh = CreateObject(\"Wscript.Shell\")\r\n"
        f'sh.CurrentDirectory = "{ROOT}"\r\n'
        f'sh.Run """{START_BAT}""", 0, False\r\n'
    )
    VBS_PATH.write_text(body, encoding="utf-16")
    return VBS_PATH


def is_autostart_on() -> bool:
    try:
        import winreg
    except ImportError:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
    except OSError:
        return False
    try:
        value, _kind = winreg.QueryValueEx(key, RUN_NAME)
    except OSError:
        return False
    finally:
        winreg.CloseKey(key)
    return bool(str(value).strip())


def set_autostart(enabled: bool) -> bool:
    try:
        import winreg
    except ImportError:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
    except OSError:
        return False
    try:
        if enabled:
            write_autostart_vbs()
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except OSError:
                pass
    finally:
        winreg.CloseKey(key)
    return is_autostart_on() if enabled else not is_autostart_on()
