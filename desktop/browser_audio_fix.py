"""Disable Chrome-wide echo cancellation for every browser profile (user)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

_PROCESS_LOCK = threading.Lock()
_PROCESS_CACHE: dict = {"at": 0.0, "rows": []}

_PROFILE_RE = re.compile(r"--profile-directory(?:=|\s+)(?P<q>\"?)(?P<name>[^\"\s]+)(?P=q)", re.I)
_USER_DATA_RE = re.compile(r"--user-data-dir(?:=|\s+)(?P<q>\"?)(?P<name>[^\"\s]+)(?P=q)", re.I)


def parse_chrome_arg(cmdline: str, flag: str) -> str:
    if not cmdline or not flag:
        return ""
    lower = cmdline.lower()
    needle = flag.lower()
    idx = lower.find(needle)
    if idx < 0:
        return ""
    pos = idx + len(flag)
    if pos < len(cmdline) and cmdline[pos] in "=:":
        pos += 1
    while pos < len(cmdline) and cmdline[pos] in " \t":
        pos += 1
    if pos >= len(cmdline):
        return ""
    if cmdline[pos] == '"':
        end = cmdline.find('"', pos + 1)
        return cmdline[pos + 1 : end] if end > 0 else cmdline[pos + 1 :]
    if cmdline[:idx].count('"') % 2 == 1:
        end = cmdline.find('"', pos)
        return cmdline[pos:end] if end > 0 else cmdline[pos:]
    end = pos
    while end < len(cmdline):
        if cmdline[end].isspace() and cmdline[end:].lstrip().startswith("--"):
            break
        end += 1
    return cmdline[pos:end].strip().strip('"')

FEATURES = "ChromeWideEchoCancellation"
FEATURE_ARG = f"--disable-features={FEATURES}"
FLAG_IDS = (
    "chrome-wide-echo-cancellation",
    "edge-wide-echo-cancellation",
    "msedge-wide-echo-cancellation",
)
STATUS_NAME = "Local State.tab-stereo-fix.status"
STATUS_STORE = Path(__file__).resolve().parent.parent / "config" / "fix-status.json"
BROWSER_PROCESSES = ("chrome.exe", "msedge.exe", "brave.exe", "chromium.exe")

INSTALLS = (
    {
        "name": "Chrome",
        "exe_names": ("chrome.exe",),
        "exe_globs": (
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        ),
        "user_data": r"%LOCALAPPDATA%\Google\Chrome\User Data",
    },
    {
        "name": "Chrome Beta",
        "exe_names": ("chrome.exe",),
        "exe_globs": (
            r"%PROGRAMFILES%\Google\Chrome Beta\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome Beta\Application\chrome.exe",
        ),
        "user_data": r"%LOCALAPPDATA%\Google\Chrome Beta\User Data",
    },
    {
        "name": "Edge",
        "exe_names": ("msedge.exe",),
        "exe_globs": (
            r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        ),
        "user_data": r"%LOCALAPPDATA%\Microsoft\Edge\User Data",
    },
    {
        "name": "Edge Beta",
        "exe_names": ("msedge.exe",),
        "exe_globs": (
            r"%PROGRAMFILES(X86)%\Microsoft\Edge Beta\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge Beta\Application\msedge.exe",
        ),
        "user_data": r"%LOCALAPPDATA%\Microsoft\Edge Beta\User Data",
    },
    {
        "name": "Brave",
        "exe_names": ("brave.exe",),
        "exe_globs": (
            r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
        ),
        "user_data": r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data",
    },
)


def expand(path: str) -> Path:
    return Path(os.path.expandvars(path)).expanduser()


def running_images() -> set[str]:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    found = set()
    lower = out.lower()
    for name in BROWSER_PROCESSES:
        if name.lower() in lower:
            found.add(name)
    return found


# Do not taskkill /IM chrome.exe (or msedge/brave). That closes every browser.


@dataclass
class BrowserProfile:
    browser: str
    exe: Path
    user_data: Path
    directory: str
    display_name: str
    email: str = ""
    selected: bool = True

    @property
    def key(self) -> str:
        return f"{self.browser}|{self.user_data}|{self.directory}"

    @property
    def label(self) -> str:
        extra = f" · {self.email}" if self.email else ""
        return f"{self.browser} / {self.display_name}{extra}"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _looks_like_id(value: str) -> bool:
    compact = "".join(ch for ch in value if ch.isalnum())
    return not compact or compact.isdigit()


def profile_display(info: dict, directory: str) -> tuple[str, str]:
    name = (
        str(info.get("gaia_given_name") or "").strip()
        or str(info.get("gaia_name") or "").strip()
        or str(info.get("name") or "").strip()
    )
    if _looks_like_id(name):
        name = "默认用户" if directory == "Default" else directory
    email = str(info.get("user_name") or "").strip()
    if _looks_like_id(email):
        email = ""
    return name, email


def profiles_from_local_state(browser: str, exe: Path, user_data: Path) -> list[BrowserProfile]:
    local_state = user_data / "Local State"
    cache: dict = {}
    last = "Default"
    if local_state.exists():
        try:
            data = read_json(local_state)
            profile = data.get("profile") or {}
            cache = profile.get("info_cache") or {}
            last = str(profile.get("last_used") or "Default")
        except (OSError, json.JSONDecodeError, TypeError):
            cache = {}
    if not cache:
        default_dir = user_data / "Default"
        if default_dir.is_dir():
            cache = {"Default": {"name": "默认用户"}}
    result: list[BrowserProfile] = []
    for directory, info in cache.items():
        if not isinstance(info, dict):
            continue
        if not (user_data / directory).is_dir():
            continue
        name, email = profile_display(info, directory)
        result.append(
            BrowserProfile(
                browser=browser,
                exe=exe,
                user_data=user_data,
                directory=directory,
                display_name=name,
                email=email,
                selected=directory == last or last == directory,
            )
        )
    if result and not any(item.selected for item in result):
        result[0].selected = True
    return result


def list_browser_processes(force: bool = False) -> list[dict]:
    now = time.time()
    with _PROCESS_LOCK:
        if not force and _PROCESS_CACHE["rows"] is not None and now - float(_PROCESS_CACHE["at"]) < 1.2:
            return list(_PROCESS_CACHE["rows"])
    script = (
        "Get-CimInstance Win32_Process -Filter \""
        "Name = 'chrome.exe' OR Name = 'msedge.exe' OR Name = 'brave.exe' OR Name = 'chromium.exe'\" | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        rows = []
    else:
        raw = (result.stdout or "").strip()
        rows = []
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = []
            if isinstance(data, dict):
                data = [data]
            for item in data:
                cmdline = str(item.get("CommandLine") or "")
                exe = str(item.get("ExecutablePath") or _exe_from_command(cmdline) or "")
                user_data = parse_chrome_arg(cmdline, "--user-data-dir")
                directory = parse_chrome_arg(cmdline, "--profile-directory") or "Default"
                rows.append(
                    {
                        "pid": int(item.get("ProcessId") or 0),
                        "ppid": int(item.get("ParentProcessId") or 0),
                        "name": str(item.get("Name") or ""),
                        "exe": exe,
                        "cmdline": cmdline,
                        "directory": directory,
                        "user_data": str(Path(user_data)) if user_data else "",
                    }
                )
    with _PROCESS_LOCK:
        _PROCESS_CACHE["at"] = time.time()
        _PROCESS_CACHE["rows"] = rows
    return list(rows)


def process_command_lines() -> list[str]:
    return [row["cmdline"] for row in list_browser_processes() if row.get("cmdline")]


def _norm_path(path) -> str:
    if not path:
        return ""
    text = str(path).strip().strip('"').replace("\\", "/")
    return os.path.normcase(os.path.normpath(text))


def _file_name(path) -> str:
    return Path(_norm_path(path).replace("\\", "/")).name.lower()


def _row_user_data(row: dict) -> str:
    raw = row.get("user_data") or ""
    if raw:
        return _norm_path(raw)
    return _norm_path(parse_chrome_arg(row.get("cmdline") or "", "--user-data-dir"))


def _product_key(path) -> str:
    lower = _norm_path(path).replace("\\", "/").lower()
    if "chrome beta" in lower:
        return "chrome-beta"
    if "edge beta" in lower:
        return "edge-beta"
    if "bravesoftware" in lower or "/brave/" in lower or lower.endswith("/brave"):
        return "brave"
    if "/microsoft/edge" in lower or "/edge/" in lower:
        return "edge"
    if "/google/chrome" in lower or "/chrome/" in lower:
        return "chrome"
    return Path(lower).name.lower()


def _same_exe(row: dict, exe: Path) -> bool:
    row_exe = row.get("exe") or ""
    return bool(row_exe) and _norm_path(row_exe) == _norm_path(exe)


def _same_product(row: dict, exe: Path) -> bool:
    row_exe = row.get("exe") or ""
    if not row_exe:
        return False
    if _norm_path(row_exe) == _norm_path(exe):
        return True
    return _product_key(row_exe) == _product_key(exe)


def belongs_to_install(row: dict, exe: Path, user_data: Path) -> bool:
    if (row.get("name") or "").lower() != _file_name(exe):
        return False
    row_data = _row_user_data(row)
    if row_data:
        if row_data != _norm_path(user_data):
            return False
        if row.get("exe") and not _same_product(row, exe):
            return False
        return True
    if "--user-data-dir" in (row.get("cmdline") or "").lower():
        return False
    if not _same_product(row, exe):
        return False
    return True


def pids_for_install(exe: Path, user_data: Path, rows: list[dict] | None = None) -> list[int]:
    rows = rows if rows is not None else list_browser_processes()
    wanted = {row["pid"] for row in rows if row.get("pid") and belongs_to_install(row, exe, user_data)}
    changed = True
    while changed:
        changed = False
        for row in rows:
            pid = row.get("pid")
            if not pid or pid in wanted or row.get("ppid") not in wanted:
                continue
            if (row.get("name") or "").lower() != exe.name.lower():
                continue
            if row.get("exe") and not _same_exe(row, exe):
                continue
            wanted.add(pid)
            changed = True
    return list(wanted)


def collect_install_pids(profiles: list[BrowserProfile], rows: list[dict] | None = None) -> tuple[list[int], list[str]]:
    rows = rows if rows is not None else list_browser_processes()
    allowed_names = {item.exe.name.lower() for item in profiles}
    allowed_exes = {_norm_path(item.exe) for item in profiles}
    pids: list[int] = []
    for user_data in unique_user_data(profiles):
        exe = next(item.exe for item in profiles if item.user_data == user_data)
        pids.extend(pids_for_install(exe, user_data, rows=rows))
    by_pid = {row["pid"]: row for row in rows if row.get("pid")}
    safe: list[int] = []
    warnings: list[str] = []
    for pid in dict.fromkeys(pids):
        row = by_pid.get(pid)
        if not row:
            continue
        name = (row.get("name") or "").lower()
        if name not in allowed_names:
            warnings.append(f"跳过其它浏览器 {name} pid {pid}")
            continue
        row_exe = _norm_path(row.get("exe") or "")
        if row_exe and row_exe not in allowed_exes:
            warnings.append(f"跳过其它安装 {row.get('exe')} pid {pid}")
            continue
        safe.append(pid)
    return safe, warnings


PREFERRED_BROWSERS = ("Chrome", "Edge", "Brave", "Chrome Beta", "Edge Beta")


def default_user_data(profiles: list[BrowserProfile]) -> Path | None:
    item = default_profile(profiles)
    return item.user_data if item else None


def default_profile(profiles: list[BrowserProfile]) -> BrowserProfile | None:
    running = [item for item in profiles if item.selected]
    pool = running or profiles
    for name in PREFERRED_BROWSERS:
        for item in pool:
            if item.browser == name:
                return item
    return pool[0] if pool else None


def kill_pids(pids: list[int]) -> None:
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid)], check=False, capture_output=True, text=True)
    if pids and not wait_pids_closed(pids, 10):
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False, capture_output=True, text=True)
        wait_pids_closed(pids, 8)


def _pid_alive(pid: int) -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return kernel32.GetLastError() == 5
    except Exception:
        return False


def wait_pids_closed(pids: list[int], timeout: float = 12.0) -> bool:
    wanted = {int(pid) for pid in pids if pid}
    if not wanted:
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(_pid_alive(pid) for pid in wanted):
            return True
        time.sleep(0.2)
    return not any(_pid_alive(pid) for pid in wanted)


def _exe_from_command(line: str) -> str:
    text = line.strip()
    if text.startswith('"'):
        parts = text.split('"', 2)
        return parts[1] if len(parts) > 1 else text
    return text.split(" ", 1)[0]


def _row_directory(row: dict) -> str:
    raw = row.get("directory") or ""
    if raw:
        return str(raw)
    return parse_chrome_arg(row.get("cmdline") or "", "--profile-directory") or "Default"


def list_visible_browser_pids() -> set[int]:
    script = (
        "Get-Process -Name chrome,msedge,brave,chromium -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowHandle -ne 0 } | "
        "Select-Object -ExpandProperty Id | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    raw = (result.stdout or "").strip()
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if isinstance(data, int):
        data = [data]
    return {int(pid) for pid in data if pid}


def is_open_session(row: dict, visible_pids: set[int] | None = None) -> bool:
    cmd = (row.get("cmdline") or "").lower()
    if "--no-startup-window" in cmd:
        return False
    if visible_pids:
        if row.get("pid") in visible_pids:
            return True
        if "--type=" in cmd:
            return False
        return True
    return "--type=" not in cmd


def install_is_running(
    exe: Path,
    user_data: Path,
    rows: list[dict] | None = None,
    visible_pids: set[int] | None = None,
) -> bool:
    rows = rows if rows is not None else list_browser_processes()
    visible_pids = visible_pids if visible_pids is not None else set()
    return any(
        belongs_to_install(row, exe, user_data) and is_open_session(row, visible_pids)
        for row in rows
    )


def mark_running_profiles(
    profiles: list[BrowserProfile],
    rows: list[dict] | None = None,
    visible_pids: set[int] | None = None,
) -> list[BrowserProfile]:
    rows = rows if rows is not None else list_browser_processes()
    visible_pids = visible_pids if visible_pids is not None else set()
    for profile in profiles:
        profile.selected = False
        for row in rows:
            if not is_open_session(row, visible_pids):
                continue
            if not belongs_to_install(row, profile.exe, profile.user_data):
                continue
            if _row_directory(row) == profile.directory:
                profile.selected = True
                break
    return profiles


def first_existing(paths: tuple[str, ...]) -> Path | None:
    for raw in paths:
        path = expand(raw)
        if path.is_file():
            return path
    return None


def discover_profiles() -> list[BrowserProfile]:
    found: list[BrowserProfile] = []
    seen: set[str] = set()
    for spec in INSTALLS:
        exe = first_existing(spec["exe_globs"])
        user_data = expand(spec["user_data"])
        if not exe or not user_data.is_dir():
            continue
        for profile in profiles_from_local_state(spec["name"], exe, user_data):
            if profile.key in seen:
                continue
            seen.add(profile.key)
            found.append(profile)
    return mark_running_profiles(found)


def disable_flags(data: dict, flag_ids: tuple[str, ...] = FLAG_IDS) -> dict:
    browser = data.setdefault("browser", {})
    existing = browser.get("enabled_labs_experiments") or []
    kept: list[str] = []
    seen: set[str] = set()
    for item in existing:
        if not isinstance(item, str):
            continue
        name = item.split("@", 1)[0]
        if name in flag_ids:
            continue
        kept.append(item)
    for name in flag_ids:
        entry = f"{name}@2"
        if entry not in seen:
            kept.append(entry)
            seen.add(entry)
    browser["enabled_labs_experiments"] = kept
    return data


def restore_flags(data: dict, flag_ids: tuple[str, ...] = FLAG_IDS) -> dict:
    browser = data.setdefault("browser", {})
    existing = browser.get("enabled_labs_experiments") or []
    browser["enabled_labs_experiments"] = [
        item
        for item in existing
        if not (isinstance(item, str) and item.split("@", 1)[0] in flag_ids)
    ]
    return data


def _write_local_state(user_data: Path, transform) -> Path | None:
    local_state = user_data / "Local State"
    if not local_state.exists():
        return None
    raw = local_state.read_text(encoding="utf-8-sig")
    data = transform(json.loads(raw))
    backup = local_state.with_name("Local State.tab-stereo-fix.bak")
    if not backup.exists():
        backup.write_text(raw, encoding="utf-8")
    local_state.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return local_state


def patch_local_state(user_data: Path) -> Path | None:
    return _write_local_state(user_data, disable_flags)


def restore_local_state(user_data: Path) -> Path | None:
    return _write_local_state(user_data, restore_flags)


def flags_disabled(user_data: Path) -> bool:
    local_state = user_data / "Local State"
    if not local_state.exists():
        return False
    try:
        data = json.loads(local_state.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    flags = (data.get("browser") or {}).get("enabled_labs_experiments") or []
    return any(
        isinstance(item, str) and item.split("@", 1)[0] in FLAG_IDS and item.endswith("@2")
        for item in flags
    )


def _status_store() -> dict:
    if not STATUS_STORE.exists():
        return {}
    try:
        data = json.loads(STATUS_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_fix_status(user_data: Path, enabled: bool) -> None:
    payload = json.dumps({"enabled": bool(enabled), "feature": FEATURES}, ensure_ascii=False)
    try:
        (user_data / STATUS_NAME).write_text(payload, encoding="utf-8")
    except OSError:
        pass
    store = _status_store()
    store[_norm_path(user_data)] = bool(enabled)
    try:
        STATUS_STORE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def fix_status_enabled(user_data: Path) -> bool:
    path = user_data / STATUS_NAME
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if bool(data.get("enabled")):
                return True
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return bool(_status_store().get(_norm_path(user_data)))


def running_with_fix(exe: Path, user_data: Path, rows: list[dict] | None = None) -> bool:
    rows = rows if rows is not None else list_browser_processes()
    needle = FEATURES.lower()
    return any(
        belongs_to_install(row, exe, user_data) and needle in (row.get("cmdline") or "").lower()
        for row in rows
    )


def is_fix_on(user_data: Path, exe: Path | None = None) -> bool:
    if flags_disabled(user_data) or fix_status_enabled(user_data):
        return True
    if exe is None:
        return False
    return running_with_fix(exe, user_data)


def launcher_name(profile: BrowserProfile) -> str:
    raw = f"{profile.browser} - {profile.display_name}（立体声）"
    cleaned = "".join("_" if ch in r'<>:"/\|?*' else ch for ch in raw)
    return cleaned[:80]


def write_launcher(profile: BrowserProfile, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{launcher_name(profile)}.bat"
    quoted_exe = f'"{profile.exe}"'
    body = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        f"start \"\" {quoted_exe} --user-data-dir=\"{profile.user_data}\" "
        f"--profile-directory=\"{profile.directory}\" {FEATURE_ARG}\r\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


GAIN_EXT_DIR = Path(__file__).resolve().parent / "gain_ext"


def write_gain_config(gain: float) -> Path:
    value = max(1.0, min(4.0, float(gain)))
    path = GAIN_EXT_DIR / "gain-config.js"
    path.write_text(
        f"document.documentElement.dataset.stereoGain = {value:.2f};\n",
        encoding="utf-8",
    )
    return path


def strip_gain_extension(user_data: Path) -> int:
    """Remove the page-gain addon so media is not hijacked into silence."""
    removed = 0
    for prefs_path in user_data.glob("*/Preferences"):
        try:
            data = json.loads(prefs_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        settings = ((data.get("extensions") or {}).get("settings")) or {}
        if not isinstance(settings, dict):
            continue
        drop = []
        for ext_id, info in settings.items():
            if not isinstance(info, dict):
                continue
            path = str(info.get("path") or info.get("install_path") or "")
            name = str((info.get("manifest") or {}).get("name") or "")
            if "gain_ext" in path.replace("\\", "/").lower() or name == "立体声增益":
                drop.append(ext_id)
        if not drop:
            continue
        for ext_id in drop:
            settings.pop(ext_id, None)
            removed += 1
        prefs_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return removed


def launch_profile(profile: BrowserProfile, *, fixed: bool = True, gain: float = 3.0) -> None:
    args = [
        str(profile.exe),
        f"--user-data-dir={profile.user_data}",
        f"--profile-directory={profile.directory}",
    ]
    if fixed:
        args.append(FEATURE_ARG)
    subprocess.Popen(args)


def patch_shortcuts() -> list[str]:
    ps = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$flag = '{FEATURE_ARG}'
$shell = New-Object -ComObject WScript.Shell
$roots = @(
  [Environment]::GetFolderPath('Desktop'),
  [Environment]::GetFolderPath('CommonDesktopDirectory'),
  [Environment]::GetFolderPath('StartMenu'),
  [Environment]::GetFolderPath('CommonStartMenu'),
  Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
)
Get-ChildItem -Path $roots -Filter *.lnk -Recurse | Where-Object {{
  $_.Name -match 'Chrome|Edge|Brave|铬|勇敢'
}} | ForEach-Object {{
  $lnk = $shell.CreateShortcut($_.FullName)
  if ($lnk.TargetPath -notmatch 'chrome|msedge|brave') {{ return }}
  $args = [string]$lnk.Arguments
  if ($args -match 'ChromeWideEchoCancellation') {{ return }}
  $lnk.Arguments = ($args + ' ' + $flag).Trim()
  $lnk.Save()
  Write-Output $_.FullName
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]


@dataclass
class FixReport:
    closed: list[str] = field(default_factory=list)
    patched_states: list[str] = field(default_factory=list)
    launchers: list[str] = field(default_factory=list)
    shortcuts: list[str] = field(default_factory=list)
    launched: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines: list[str] = []
        if self.closed:
            lines.append("已关闭：" + ", ".join(self.closed))
        if self.patched_states:
            lines.append("已写入实验项：")
            lines.extend(f"  {item}" for item in self.patched_states)
        if self.launchers:
            lines.append("已生成整用户启动器：")
            lines.extend(f"  {item}" for item in self.launchers)
        if self.shortcuts:
            lines.append("已改快捷方式：")
            lines.extend(f"  {item}" for item in self.shortcuts)
        if self.launched:
            lines.append("已重新打开：")
            lines.extend(f"  {item}" for item in self.launched)
        if self.warnings:
            lines.append("注意：")
            lines.extend(f"  {item}" for item in self.warnings)
        if self.errors:
            lines.append("失败：")
            lines.extend(f"  {item}" for item in self.errors)
        if not lines:
            lines.append("没有需要处理的浏览器用户。")
        return "\n".join(lines)


def profiles_sharing_install(selected: list[BrowserProfile], all_profiles: list[BrowserProfile] | None = None) -> list[BrowserProfile]:
    """One User Data is one process tree. Also reopen other running profiles there."""
    all_profiles = all_profiles if all_profiles is not None else discover_profiles()
    wanted = {item.user_data for item in selected}
    by_key: dict[str, BrowserProfile] = {}
    for item in selected:
        by_key[item.key] = item
    for item in all_profiles:
        if item.user_data in wanted and item.selected:
            by_key.setdefault(item.key, item)
    return list(by_key.values())


def unique_user_data(profiles: list[BrowserProfile]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for profile in profiles:
        if profile.user_data in seen:
            continue
        seen.add(profile.user_data)
        result.append(profile.user_data)
    return result


def one_install_only(profiles: list[BrowserProfile]) -> tuple[list[BrowserProfile], list[str]]:
    """Keep a single browser install. Never close, patch, or retune the others."""
    if not profiles:
        return [], []
    keep = profiles[0].user_data
    kept = [item for item in profiles if item.user_data == keep]
    dropped = [item.label for item in profiles if item.user_data != keep]
    notes = [f"其它浏览器不处理：{', '.join(dropped)}"] if dropped else []
    return kept, notes


@dataclass
class BrowserInstall:
    browser: str
    exe: Path
    user_data: Path
    profiles: list[BrowserProfile] = field(default_factory=list)

    @property
    def running(self) -> bool:
        return any(item.selected for item in self.profiles)

    @property
    def fixed(self) -> bool:
        return is_fix_on(self.user_data, self.exe)

    @property
    def running_profiles(self) -> list[BrowserProfile]:
        return [item for item in self.profiles if item.selected]


def group_installs(profiles: list[BrowserProfile]) -> list[BrowserInstall]:
    order: list[BrowserInstall] = []
    buckets: dict[str, BrowserInstall] = {}
    for item in profiles:
        key = f"{item.browser}|{_norm_path(item.user_data)}"
        if key not in buckets:
            inst = BrowserInstall(item.browser, item.exe, item.user_data, [])
            buckets[key] = inst
            order.append(inst)
        buckets[key].profiles.append(item)
    return order


def apply_fix(
    profiles: list[BrowserProfile],
    *,
    enabled: bool = True,
    close_first: bool = True,
    relaunch: bool = True,
    desktop_copies: bool = False,
    patch_links: bool = False,
    launcher_dir: Path | None = None,
    progress=None,
    gain: float = 3.0,
) -> FixReport:
    report = FixReport()

    def note(message: str) -> None:
        if progress:
            progress(message)

    if not profiles:
        report.warnings.append("没有选中任何浏览器用户。")
        return report

    profiles, ignored = one_install_only(profiles)
    report.warnings.extend(ignored)
    browser = profiles[0].browser

    launcher_dir = launcher_dir or (Path(__file__).resolve().parent.parent / "launchers")
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))

    if close_first:
        pids, skip_notes = collect_install_pids(profiles)
        report.warnings.extend(skip_notes)
        if pids:
            note(f"正在关闭 {browser}…")
            kill_pids(pids)
            report.closed = [f"pid {pid}" for pid in pids]
            if not wait_pids_closed(pids, 16):
                report.errors.append(f"{browser} 还没完全退出，已取消写入，以免动到其它浏览器。")
                return report
            time.sleep(0.4)

    note(f"正在写入 {browser} 的设置…")
    for user_data in unique_user_data(profiles):
        try:
            patched = patch_local_state(user_data) if enabled else restore_local_state(user_data)
            if patched:
                report.patched_states.append(str(patched))
            else:
                report.warnings.append(f"没有 Local State：{user_data}")
            write_fix_status(user_data, enabled)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"写入 {user_data} 失败：{exc}")

    for user_data in unique_user_data(profiles):
        if enabled and not flags_disabled(user_data):
            report.warnings.append(f"{browser} 可能不会保留实验项，已用启动参数和软件记录标记为已修复。")
        if not enabled and flags_disabled(user_data):
            report.warnings.append(f"{browser} 的实验项还在，已按关闭处理。")

    if patch_links:
        report.warnings.append("已跳过改快捷方式，避免影响其它浏览器。")

    if enabled and desktop_copies:
        for profile in profiles:
            try:
                path = write_launcher(profile, launcher_dir)
                report.launchers.append(str(path))
                if desktop.is_dir():
                    shutil.copy2(path, desktop / path.name)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"启动器 {profile.label} 失败：{exc}")

    if report.errors:
        return report

    for user_data in unique_user_data(profiles):
        stripped = strip_gain_extension(user_data)
        if stripped:
            report.warnings.append("已去掉会把网页静音的增益插件。")

    if relaunch:
        note(f"正在打开你选的用户…")
        for profile in profiles:
            try:
                launch_profile(profile, fixed=enabled, gain=gain)
                report.launched.append(profile.label)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"启动 {profile.label} 失败：{exc}")
        time.sleep(1.0)
        if enabled:
            try:
                from app_volume import set_browser_volume

                exe_paths = {str(item.exe) for item in profiles}
                changed = set_browser_volume(1.0, exe_paths=exe_paths)
                report.warnings.append(f"已把这套浏览器系统音量拉满（会话 {changed} 个）。")
            except Exception:
                pass

    note("完成")
    return report


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--discover" in argv:
        for item in discover_profiles():
            line = f"{item.label}\t{item.directory}\t{item.exe}"
            try:
                print(line)
            except UnicodeEncodeError:
                sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        return 0
    print("Use: python -m desktop.app")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
