"""Native host: plugin toggle restarts this browser user with Wide AEC on/off."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from browser_audio_fix import (
    _PROFILE_RE,
    _USER_DATA_RE,
    _exe_from_command,
    collect_install_pids,
    discover_profiles,
    flags_disabled,
    kill_pids,
    launch_profile,
    one_install_only,
    patch_local_state,
    restore_local_state,
    unique_user_data,
)

HOST_NAME = "com.tabstereofix.host"
EXTENSION_DIR = Path(__file__).resolve().parent.parent / "extension"
MANIFEST_PATH = Path(__file__).resolve().parent / "native-host.json"
HOST_BAT = Path(__file__).resolve().parent / "native_host.bat"
REG_PATHS = (
    r"Software\Google\Chrome\NativeMessagingHosts\com.tabstereofix.host",
    r"Software\Chromium\NativeMessagingHosts\com.tabstereofix.host",
    r"Software\Microsoft\Edge\NativeMessagingHosts\com.tabstereofix.host",
    r"Software\BraveSoftware\Brave\NativeMessagingHosts\com.tabstereofix.host",
)


def log(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def read_message() -> dict | None:
    raw = sys.stdin.buffer.read(4)
    if not raw:
        return None
    length = struct.unpack("<I", raw)[0]
    payload = sys.stdin.buffer.read(length)
    return json.loads(payload.decode("utf-8"))


def send_message(data: dict) -> None:
    encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def unpacked_ids(folder: Path) -> list[str]:
    paths = {
        str(folder.resolve()),
        str(folder.resolve()).replace("/", "\\"),
        os.path.normpath(str(folder.resolve())),
    }
    ids: list[str] = []
    for path in paths:
        for encoding in ("utf-8", "utf-16-le"):
            digest = hashlib.sha256(path.encode(encoding)).digest()[:16]
            ids.append("".join(chr(ord("a") + (byte >> 4)) + chr(ord("a") + (byte & 0xF)) for byte in digest))
    return list(dict.fromkeys(ids))


def ids_from_preferences() -> list[str]:
    roots = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge Beta\User Data")),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")),
    ]
    needle = "tab-stereo-fix"
    found: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for prefs in root.glob("*/Preferences"):
            try:
                text = prefs.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue
            if needle not in text.replace("/", "\\") and needle not in text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            settings = ((data.get("extensions") or {}).get("settings") or {})
            for ext_id, info in settings.items():
                path = str((info or {}).get("path") or "")
                if needle in path.replace("/", "\\"):
                    found.append(ext_id)
    return list(dict.fromkeys(found))


def write_host_manifest() -> list[str]:
    ids = unpacked_ids(EXTENSION_DIR) + ids_from_preferences()
    extra = Path(__file__).resolve().parent / "extension-id.txt"
    if extra.exists():
        ids.extend(line.strip() for line in extra.read_text(encoding="utf-8").splitlines() if line.strip())
    ids = list(dict.fromkeys(ids))
    HOST_BAT.write_text(
        f'@echo off\r\n"{sys.executable}" -u "{Path(__file__).resolve()}" %*\r\n',
        encoding="utf-8",
    )
    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "name": HOST_NAME,
                "description": "Browser stereo fix native host",
                "path": str(HOST_BAT),
                "type": "stdio",
                "allowed_origins": [f"chrome-extension://{item}/" for item in ids],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    for reg_path in REG_PATHS:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(MANIFEST_PATH))
        winreg.CloseKey(key)
    return ids


def process_info(pid: int) -> dict | None:
    if not pid:
        return None
    script = (
        f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}'; "
        "if ($p) { $p | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return None
    raw = (result.stdout or "").strip()
    if not raw:
        return None
    try:
        item = json.loads(raw)
    except json.JSONDecodeError:
        return None
    cmdline = str(item.get("CommandLine") or "")
    return {
        "pid": int(item.get("ProcessId") or 0),
        "ppid": int(item.get("ParentProcessId") or 0),
        "name": str(item.get("Name") or ""),
        "exe": str(item.get("ExecutablePath") or _exe_from_command(cmdline) or ""),
        "cmdline": cmdline,
    }


def detect_caller() -> dict | None:
    pid = os.getppid()
    for _ in range(8):
        info = process_info(pid)
        if not info:
            break
        name = info["name"].lower()
        if name in {"chrome.exe", "msedge.exe", "brave.exe", "chromium.exe"}:
            cmdline = info["cmdline"]
            profile_match = _PROFILE_RE.search(cmdline)
            data_match = _USER_DATA_RE.search(cmdline)
            return {
                "image": info["name"],
                "exe": info["exe"],
                "directory": profile_match.group("name") if profile_match else "Default",
                "user_data": str(Path(data_match.group("name"))) if data_match else "",
            }
        pid = info["ppid"]
    return None


def profiles_for_caller(caller: dict | None):
    profiles = discover_profiles()
    if not caller:
        return []
    image = Path(caller.get("exe") or caller.get("image") or "chrome.exe").name.lower()
    exe_raw = caller.get("exe") or ""
    caller_exe = Path(exe_raw) if exe_raw else None
    user_data = (caller.get("user_data") or "").lower()
    directory = caller.get("directory") or "Default"
    matched = []
    for item in profiles:
        if item.exe.name.lower() != image:
            continue
        if caller_exe is not None and Path(item.exe) != caller_exe:
            continue
        if user_data and str(item.user_data).lower() != user_data:
            continue
        matched.append(item)
    running = [item for item in matched if item.selected]
    if running:
        return running
    exact = [item for item in matched if item.directory == directory]
    return exact or matched[:1]


def apply_toggle(enabled: bool, caller: dict | None = None) -> dict:
    caller = caller or detect_caller()
    profiles = profiles_for_caller(caller)
    if not profiles:
        return {"ok": False, "error": "没有定位到当前这个浏览器，已取消，以免关掉其它浏览器。"}
    profiles, _ignored = one_install_only(profiles)

    pids, _notes = collect_install_pids(profiles)
    if pids:
        kill_pids(pids)

    for user_data in unique_user_data(profiles):
        if enabled:
            patch_local_state(user_data)
        else:
            restore_local_state(user_data)

    for profile in profiles:
        launch_profile(profile, fixed=enabled)
    if enabled:
        import time
        from app_volume import set_browser_volume

        time.sleep(2.5)
        set_browser_volume(1.0, exe_paths={str(item.exe) for item in profiles})
    return {
        "ok": True,
        "enabled": enabled,
        "users": [item.label for item in profiles],
    }


def status_payload(caller: dict | None = None) -> dict:
    caller = caller or detect_caller()
    profiles = profiles_for_caller(caller) or []
    enabled = any(flags_disabled(item.user_data) for item in profiles)
    return {
        "ok": True,
        "enabled": enabled,
        "installed": True,
        "users": [item.label for item in profiles],
    }


def main() -> int:
    if "--register" in sys.argv:
        ids = write_host_manifest()
        print("registered", HOST_NAME)
        print("ids", ",".join(ids))
        return 0

    if "--apply" in sys.argv:
        enabled = "--on" in sys.argv
        caller = None
        if "--image" in sys.argv:
            args = sys.argv
            def arg_after(flag: str) -> str:
                return args[args.index(flag) + 1] if flag in args and args.index(flag) + 1 < len(args) else ""

            caller = {
                "image": arg_after("--image"),
                "exe": arg_after("--exe"),
                "user_data": arg_after("--user-data"),
                "directory": arg_after("--directory") or "Default",
            }
        apply_toggle(enabled, caller)
        return 0

    write_host_manifest()
    message = read_message()
    if not message:
        return 0
    action = message.get("type") or message.get("action")
    caller = detect_caller()
    if action == "status":
        send_message(status_payload(caller))
        return 0
    if action == "volume":
        from app_volume import set_browser_volume

        level = max(0.0, min(1.0, float(message.get("level") or 1)))
        exe = (caller or {}).get("exe") or ""
        changed = set_browser_volume(level, exe_paths={exe} if exe else None)
        send_message({"ok": True, "changed": changed, "level": level})
        return 0
    if action == "set":
        enabled = bool(message.get("enabled"))
        send_message({"ok": True, "restarting": True, "enabled": enabled})
        flags = 0x00000008 | 0x00000200
        apply_cmd = [sys.executable, str(Path(__file__).resolve()), "--apply", "--on" if enabled else "--off"]
        if caller:
            apply_cmd.extend(
                [
                    "--image", caller.get("image") or "",
                    "--exe", caller.get("exe") or "",
                    "--user-data", caller.get("user_data") or "",
                    "--directory", caller.get("directory") or "Default",
                ]
            )
        subprocess.Popen(apply_cmd, creationflags=flags, close_fds=True)
        return 0
    send_message({"ok": False, "error": "unknown action"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
