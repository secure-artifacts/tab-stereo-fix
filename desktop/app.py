"""GUI: pick one browser install and toggle Wide AEC. Other browsers stay untouched."""

from __future__ import annotations

import json
import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from desktop.app_volume import set_browser_volume
    from desktop.autostart import is_autostart_on, set_autostart
    from desktop.paths import asset_file, config_file
    from desktop.browser_audio_fix import (
        apply_fix,
        default_profile,
        discover_profiles,
        filter_profiles_by_name,
        group_installs,
        one_install_only,
    )
except ImportError:  # pragma: no cover
    from app_volume import set_browser_volume
    from autostart import is_autostart_on, set_autostart
    from paths import asset_file, config_file
    from browser_audio_fix import (
        apply_fix,
        default_profile,
        discover_profiles,
        filter_profiles_by_name,
        group_installs,
        one_install_only,
    )

WINDOW_TITLE = "立体声修复 - 选用户"
OLD_TITLES = (WINDOW_TITLE,)
STATE_PATH = config_file("ui-state.json")
ERROR_PATH = config_file("last-error.txt")


def load_ui_state() -> dict:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data


def save_ui_state(user_data=None, profile_key: str | None = None, gain_percent: int | None = None) -> None:
    data = load_ui_state()
    if user_data is not None:
        data["user_data"] = str(user_data)
    if profile_key is not None:
        data["profile_key"] = str(profile_key)
    if gain_percent is not None:
        data["gain_percent"] = int(gain_percent)
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def load_last_user_data() -> str:
    return str(load_ui_state().get("user_data") or "")


def focus_existing_window() -> bool:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = 0
        for title in OLD_TITLES:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                break
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry("620x680")
        self.minsize(540, 560)
        self.configure(bg="#f3f6fb")
        self.installs = []
        self.profiles = []
        self._snapshot = []
        self.choice = tk.StringVar(value="")
        self.search_var = tk.StringVar(value="")
        self.busy = False
        self._refreshing = False
        self._icon_photos = []
        self._apply_app_icon()
        self._build()
        self.after(80, self.refresh)

    def _load_photo(self, name: str):
        path = asset_file(name)
        if not path.is_file():
            return None
        try:
            photo = tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None
        self._icon_photos.append(photo)
        return photo

    def _apply_app_icon(self) -> None:
        ico = asset_file("app.ico")
        if ico.is_file():
            try:
                self.iconbitmap(default=str(ico))
            except tk.TclError:
                pass
        photo = self._load_photo("app-48.png") or self._load_photo("app.png")
        if photo is not None:
            try:
                self.iconphoto(True, photo)
            except tk.TclError:
                pass

    def _build(self) -> None:
        header = tk.Frame(self, bg="#1d4ed8")
        header.pack(fill="x")
        title_row = tk.Frame(header, bg="#1d4ed8")
        title_row.pack(fill="x", padx=16, pady=(14, 2))
        avatar = self._load_photo("app-48.png")
        if avatar is not None:
            tk.Label(title_row, image=avatar, bg="#1d4ed8").pack(side="left", padx=(0, 10))
        tk.Label(
            title_row,
            text="立体声修复",
            fg="white",
            bg="#1d4ed8",
            font=("Microsoft YaHei UI", 16, "bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        tk.Label(
            header,
            text="关掉 Wide AEC，让浏览器声音进入 VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1。必须从本软件点「打开」来启动浏览器。",
            fg="#dbeafe",
            bg="#1d4ed8",
            font=("Microsoft YaHei UI", 9),
            wraplength=580,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 14))

        body = tk.Frame(self, bg="#f3f6fb")
        body.pack(fill="both", expand=True, padx=14, pady=12)

        self.status = tk.Label(
            body,
            text="正在扫描…",
            bg="#e0e7ff",
            fg="#1e3a8a",
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            padx=10,
            pady=8,
        )
        self.status.pack(fill="x")

        list_wrap = tk.LabelFrame(
            body,
            text="选择一个用户",
            bg="#f3f6fb",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        list_wrap.pack(fill="both", expand=True, pady=(10, 8))
        search_row = tk.Frame(list_wrap, bg="#f3f6fb")
        search_row.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(
            search_row,
            text="搜索用户名字",
            bg="#f3f6fb",
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left")
        ttk.Entry(search_row, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.search_var.trace_add("write", lambda *_args: self._paint_list())
        canvas = tk.Canvas(list_wrap, bg="#ffffff", highlightthickness=0, height=260)
        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas, bg="#ffffff")
        self.list_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="right", fill="y", padx=(0, 8), pady=8)

        def on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        help_box = tk.LabelFrame(
            body,
            text="使用说明",
            bg="#f3f6fb",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        help_box.pack(fill="x", pady=(0, 8))
        tk.Label(
            help_box,
            text=(
                "1. 选一个用户，点「打开（关掉 Wide AEC）」。浏览器必须由本软件启动。\n"
                "2. 关掉这套浏览器后，不能从任务栏、开始菜单或桌面图标再开。"
                "那样声音进不了 VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1。\n"
                "3. 要继续用，再打开本软件，选同一用户，再点「打开」。\n"
                "4. 要恢复原来的回声消除，选同一用户，点「关闭（恢复）」。\n"
                "5. 只动你选的这一套。其它浏览器不关。不改 VoiceMeeter / AUX / CABLE / Line 1。\n"
                "6. 「开机启动」只打开本软件窗口，不会自动打开浏览器。开机后仍要点「打开」。"
            ),
            bg="#fff7ed",
            fg="#9a3412",
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="w",
            wraplength=560,
            padx=10,
            pady=8,
        ).pack(fill="x")

        self.progress = tk.Label(
            body,
            text="选好后点「打开」。关掉浏览器后，必须再回到这里点「打开」，不要从图标自己开。",
            bg="#f8fafc",
            fg="#334155",
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            padx=10,
            pady=8,
        )
        self.progress.pack(fill="x")

        gain_row = tk.Frame(body, bg="#f3f6fb")
        gain_row.pack(fill="x", pady=(8, 0))
        tk.Label(
            gain_row,
            text="这套浏览器增益",
            bg="#f3f6fb",
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left")
        saved_gain = int(load_ui_state().get("gain_percent") or 300)
        self.gain_var = tk.IntVar(value=max(100, min(400, saved_gain)))
        self.gain_label = tk.Label(
            gain_row,
            text=f"{self.gain_var.get()}%",
            bg="#f3f6fb",
            font=("Microsoft YaHei UI", 9, "bold"),
            width=6,
        )
        self.gain_label.pack(side="right")
        self.gain_scale = ttk.Scale(
            gain_row,
            from_=100,
            to=400,
            variable=self.gain_var,
            command=self._on_gain,
        )
        self.gain_scale.pack(side="left", fill="x", expand=True, padx=8)

        buttons = tk.Frame(body, bg="#f3f6fb")
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="刷新", command=self.refresh).pack(side="left")
        self.autostart_btn = ttk.Button(buttons, text="开机启动：关", command=self.toggle_autostart)
        self.autostart_btn.pack(side="left", padx=6)
        self._refresh_autostart_button()
        ttk.Button(buttons, text="只加大这套音量", command=self.boost_volume).pack(side="left")
        self.off_btn = ttk.Button(buttons, text="关闭（恢复）", command=lambda: self.apply(False))
        self.on_btn = ttk.Button(buttons, text="打开（关掉 Wide AEC）", command=lambda: self.apply(True))
        self.off_btn.pack(side="right")
        self.on_btn.pack(side="right", padx=6)

        self.log = tk.Text(
            body,
            height=9,
            wrap="word",
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
        )
        self.log.pack(fill="both", expand=True)
        self.log.insert("1.0", "必须从本软件点「打开」启动浏览器。\n")
        self.log.insert("end", "关掉后再从任务栏/开始菜单/桌面图标打开，声音进不了立体声混音。\n")
        self.log.insert("end", "只打开你选的那一个用户。其它浏览器不关、不改音量。\n")
        self.log.configure(state="disabled")

    def _write_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", text)
        self.log.configure(state="disabled")

    def _set_progress(self, text: str, *, ok: bool | None = None) -> None:
        if ok is True:
            self.progress.configure(text=text, bg="#ecfdf3", fg="#166534")
        elif ok is False:
            self.progress.configure(text=text, bg="#fef2f2", fg="#991b1b")
        else:
            self.progress.configure(text=text, bg="#f8fafc", fg="#334155")

    def selected_profile(self):
        key = self.choice.get()
        for item in self.profiles:
            if item.key == key:
                return item
        return None

    def refresh(self) -> None:
        if self.busy or self._refreshing:
            return
        self._refreshing = True
        last = self.choice.get()
        self.status.configure(text="正在扫描…", bg="#e0e7ff", fg="#1e3a8a")

        def work() -> None:
            try:
                profiles = discover_profiles()
                installs = group_installs(profiles)
                snapshot = [
                    (item, item.running, item.fixed, list(item.profiles))
                    for item in installs
                ]
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._refresh_failed(exc))
                return
            self.after(0, lambda: self._render_profiles(profiles, snapshot, last))

        threading.Thread(target=work, daemon=True).start()

    def _refresh_failed(self, exc: Exception) -> None:
        self._refreshing = False
        self.status.configure(text=f"扫描失败：{exc}", bg="#fef2f2", fg="#991b1b")

    def _render_profiles(self, profiles, snapshot, last: str) -> None:
        self._refreshing = False
        self.profiles = profiles
        self._snapshot = snapshot
        self.installs = [item for item, _running, _fixed, _items in snapshot]
        if self.busy:
            return
        if not profiles:
            self._paint_list()
            self.status.configure(text="没有可处理的浏览器。", bg="#fef3c7", fg="#92400e")
            return

        remembered = last or str(load_ui_state().get("profile_key") or "")
        keys = {item.key for item in profiles}
        if remembered in keys:
            pick = remembered
        else:
            target = default_profile(profiles)
            pick = target.key if target else profiles[0].key
        self.choice.set(pick)
        self._paint_list()
        self._on_choice()

    def _paint_list(self) -> None:
        if self.busy or not hasattr(self, "list_frame"):
            return
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.profiles:
            tk.Label(
                self.list_frame,
                text="没有找到 Chrome / Edge / Brave。",
                bg="#ffffff",
                fg="#64748b",
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w")
            return

        visible_keys = {item.key for item in filter_profiles_by_name(self.profiles, self.search_var.get())}
        shown = 0
        for install, running, fixed, items in self._snapshot:
            keep = [item for item in items if item.key in visible_keys]
            if not keep:
                continue
            tk.Label(
                self.list_frame,
                text=f"{install.browser}（{'正在运行' if running else '未运行'} · {'已修复' if fixed else '未修复'}）",
                bg="#ffffff",
                fg="#1d4ed8",
                font=("Microsoft YaHei UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(8, 2))
            for item in keep:
                bits = []
                bits.append("正在运行" if item.selected else "未运行")
                bits.append("已修复" if fixed else "未修复")
                extra = f"（{' · '.join(bits)}）" if bits else ""
                ttk.Radiobutton(
                    self.list_frame,
                    text=f"{item.display_name}{extra}",
                    value=item.key,
                    variable=self.choice,
                    command=self._on_choice,
                ).pack(anchor="w", pady=1)
                shown += 1
        if shown == 0:
            tk.Label(
                self.list_frame,
                text="没有叫这个名字的用户。",
                bg="#ffffff",
                fg="#64748b",
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w", pady=8)

    def _on_choice(self) -> None:
        selected = self.selected_profile()
        if not selected:
            return
        save_ui_state(
            user_data=selected.user_data,
            profile_key=selected.key,
            gain_percent=int(self.gain_var.get()),
        )
        others = sorted(
            {
                item.browser
                for item in self.profiles
                if item.selected and item.key != selected.key and item.user_data != selected.user_data
            }
        )
        stay = f" 其它浏览器完全不动：{'、'.join(others)}。" if others else ""
        self.status.configure(
            text=f"当前：{selected.label}。只打开这一个。{stay}",
            bg="#ecfdf3",
            fg="#166534",
        )
        self._set_progress(
            f"点「打开」启动 {selected.label}。关掉后必须再从本软件打开，从图标自己开声音进不了立体声混音。"
        )

    def _on_gain(self, _value=None) -> None:
        value = int(round(float(self.gain_var.get()) / 25) * 25)
        value = max(100, min(400, value))
        if value != int(self.gain_var.get()):
            self.gain_var.set(value)
        self.gain_label.configure(text=f"{value}%")
        save_ui_state(gain_percent=value)

    def _refresh_autostart_button(self) -> None:
        on = is_autostart_on()
        self.autostart_btn.configure(text="开机启动：开" if on else "开机启动：关")

    def toggle_autostart(self) -> None:
        want = not is_autostart_on()
        ok = set_autostart(want)
        self._refresh_autostart_button()
        if not ok:
            messagebox.showerror("开机启动", "没能改开机启动。")
            return
        self._set_progress(
            "已打开开机启动。开机后只出现本软件，仍要点「打开」才能启动浏览器。"
            if want
            else "已关闭开机启动。",
            ok=True,
        )

    def boost_volume(self) -> None:
        selected = self.selected_profile()
        if not selected:
            messagebox.showwarning("还没选", "请先选一个用户。")
            return
        exe = str(selected.exe)
        browser = selected.browser

        def work() -> None:
            changed = set_browser_volume(1.0, exe_paths={exe})
            self.after(
                0,
                lambda: self._set_progress(
                    f"已拉满 {browser} 的系统音量（{changed} 个会话）。",
                    ok=True,
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def apply(self, enabled: bool) -> None:
        if self.busy:
            return
        selected = self.selected_profile()
        if not selected:
            messagebox.showwarning("还没选", "请先选一个用户。")
            return
        profiles, _ignored = one_install_only([selected])
        others = sorted(
            {
                item.browser
                for item in self.profiles
                if item.selected and item.user_data != selected.user_data
            }
        )
        stay = f"\n其它浏览器完全不动：{'、'.join(others)}" if others else ""
        same_running = [
            item.display_name
            for item in self.profiles
            if item.user_data == selected.user_data and item.selected and item.key != selected.key
        ]
        same_note = (
            f"\n同一套里正在开的「{'、'.join(same_running)}」会先关掉，然后只打开你选的这个。"
            if same_running
            else "\n同一套里的其它用户不会被打开。"
        )
        action = "打开（关掉 Wide AEC）" if enabled else "关闭（恢复原来的回声消除）"
        gain = max(1.0, min(4.0, int(self.gain_var.get()) / 100))
        remember = ""
        if not messagebox.askyesno(
            action,
            f"只打开这一个用户：\n· {selected.label}{same_note}{stay}\n\n"
            "关掉后再从任务栏或图标打开，声音进不了立体声混音。必须再回到本软件点「打开」。\n\n继续？",
        ):
            return
        self.busy = True
        self.on_btn.configure(state="disabled")
        self.off_btn.configure(state="disabled")
        self._set_progress(f"正在打开 {selected.label}…")

        def work() -> None:
            report = apply_fix(
                profiles,
                enabled=enabled,
                close_first=True,
                relaunch=True if enabled else selected.selected,
                desktop_copies=False,
                patch_links=False,
                gain=gain,
                progress=lambda message: self.after(0, lambda m=message: self._set_progress(m)),
            )
            self.after(0, lambda: self._finish(report, enabled))

        threading.Thread(target=work, daemon=True).start()

    def _finish(self, report, enabled: bool) -> None:
        self.busy = False
        self.on_btn.configure(state="normal")
        self.off_btn.configure(state="normal")
        self._write_log(report.as_text())
        self.after(800, self.refresh)
        if report.errors:
            self._set_progress("没有完成。", ok=False)
            messagebox.showerror("没有完成", "\n".join(report.errors[:6]))
            return
        self._set_progress("已完成。其它浏览器没有动。", ok=True)
        messagebox.showinfo(
            "完成",
            "已打开。以后这套浏览器关掉了，必须再从本软件点「打开」。从任务栏或图标自己开，声音进不了立体声混音。"
            if enabled
            else "已关闭。这套浏览器恢复原来的回声消除。",
        )


def main() -> None:
    try:
        app = App()
        app.mainloop()
    except Exception:
        ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
        ERROR_PATH.write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
