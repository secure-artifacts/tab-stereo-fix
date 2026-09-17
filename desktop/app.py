"""GUI: pick one or more browser users and toggle Wide AEC. Unchecked browsers stay untouched."""

from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from desktop.app_volume import set_browser_volume
    from desktop.autostart import is_autostart_on, set_autostart
    from desktop.categories import (
        ALL,
        UNCATEGORIZED,
        add_category,
        assignments,
        category_names,
        category_of,
        delete_category,
        filter_options,
        rename_category,
        set_category,
    )
    from desktop.paths import asset_file, config_file
    from desktop.browser_audio_fix import (
        apply_fix,
        default_profile,
        discover_profiles,
        filter_profiles_by_name,
        group_installs,
    )
    from desktop.i18n import (
        LANGUAGE_NAMES,
        SUPPORTED,
        all_window_titles,
        category_from_label,
        category_label,
        current_language,
        resolve_language,
        set_language,
        t,
        ui_font,
    )
except ImportError:  # pragma: no cover
    from app_volume import set_browser_volume
    from autostart import is_autostart_on, set_autostart
    from categories import (
        ALL,
        UNCATEGORIZED,
        add_category,
        assignments,
        category_names,
        category_of,
        delete_category,
        filter_options,
        rename_category,
        set_category,
    )
    from paths import asset_file, config_file
    from browser_audio_fix import (
        apply_fix,
        default_profile,
        discover_profiles,
        filter_profiles_by_name,
        group_installs,
    )
    from i18n import (
        LANGUAGE_NAMES,
        SUPPORTED,
        all_window_titles,
        category_from_label,
        category_label,
        current_language,
        resolve_language,
        set_language,
        t,
        ui_font,
    )

WINDOW_TITLE = t("window_title")
OLD_TITLES = all_window_titles()
STATE_PATH = config_file("ui-state.json")
ERROR_PATH = config_file("last-error.txt")


def _join_names(names: list[str]) -> str:
    return ("、" if current_language() == "zh" else ", ").join(names)


def load_ui_state() -> dict:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data


def save_ui_state(
    user_data=None,
    profile_key: str | None = None,
    profile_keys: list[str] | None = None,
    gain_percent: int | None = None,
    language: str | None = None,
) -> None:
    data = load_ui_state()
    if user_data is not None:
        data["user_data"] = str(user_data)
    if profile_keys is not None:
        data["profile_keys"] = [str(item) for item in profile_keys]
        if profile_keys:
            data["profile_key"] = str(profile_keys[0])
    elif profile_key is not None:
        data["profile_key"] = str(profile_key)
    if gain_percent is not None:
        data["gain_percent"] = int(gain_percent)
    if language is not None:
        data["language"] = str(language)
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def load_last_user_data() -> str:
    return str(load_ui_state().get("user_data") or "")


def work_area() -> tuple[int, int, int, int]:
    try:
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        area = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):
            return area.left, area.top, area.right - area.left, area.bottom - area.top
    except Exception:
        pass
    return 0, 0, 1280, 720


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
        set_language(resolve_language(str(load_ui_state().get("language") or "")))
        self.title(t("window_title"))
        self.configure(bg="#f3f6fb")
        self.installs = []
        self.profiles = []
        self._snapshot = []
        self.checked_keys: set[str] = set()
        self._check_vars = []
        self.search_var = tk.StringVar(value="")
        saved_gain = int(load_ui_state().get("gain_percent") or 300)
        self.gain_var = tk.IntVar(value=max(100, min(400, saved_gain)))
        self.category_filter = tk.StringVar(value=ALL)
        self.nav_kind = "category"
        self.browser_filter = ""
        self.busy = False
        self._refreshing = False
        self._painting = False
        self._help_open = False
        self._cat_vars = []
        self._icon_photos = []
        self.search_var.trace_add("write", lambda *_args: self._paint_list())
        self._apply_app_icon()
        self._build()
        self.bind("<Configure>", self._on_root_resize, add="+")
        self._fit_to_screen()
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

    def _fit_to_screen(self) -> None:
        left, top, width, height = work_area()
        win_w, win_h = 780, 620
        if width < win_w + 16:
            win_w = max(700, width - 16)
        if height < win_h + 16:
            win_h = max(540, height - 16)
        x = left + max(0, (width - win_w) // 2)
        y = top + max(0, (height - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(min(700, win_w), min(540, win_h))

    def _build(self) -> None:
        self.columnconfigure(0, weight=0, minsize=156)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg="#eef2f7", width=156)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        brand = tk.Frame(sidebar, bg="#eef2f7")
        brand.pack(fill="x", padx=8, pady=(8, 2))
        avatar = self._load_photo("app-48.png")
        if avatar is not None:
            tk.Label(brand, image=avatar, bg="#eef2f7").pack(side="left", padx=(0, 6))
        tk.Label(
            brand,
            text=t("categories"),
            bg="#eef2f7",
            fg="#0f172a",
            font=ui_font(10, bold=True),
            anchor="w",
        ).pack(side="left")

        self.sidebar_items = tk.Frame(sidebar, bg="#eef2f7")
        self.sidebar_items.pack(fill="x", padx=6, pady=(4, 4))

        tools = tk.Frame(sidebar, bg="#eef2f7")
        tools.pack(fill="x", padx=6, pady=(2, 8))
        ttk.Button(tools, text=t("new_category"), command=self.create_category).pack(fill="x", pady=1)
        ttk.Button(tools, text=t("rename"), command=self.rename_sidebar_category).pack(fill="x", pady=1)
        ttk.Button(tools, text=t("delete_category"), command=self.delete_sidebar_category).pack(fill="x", pady=1)

        main = tk.Frame(self, bg="#f3f6fb")
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        header = tk.Frame(main, bg="#1d4ed8")
        header.grid(row=0, column=0, sticky="ew")
        title_row = tk.Frame(header, bg="#1d4ed8")
        title_row.pack(fill="x", padx=12, pady=(8, 0))
        self.lang_btn = tk.Button(
            title_row,
            text=t("language"),
            command=self._show_language_menu,
            bg="#93c5fd",
            fg="#1e3a8a",
            activebackground="#60a5fa",
            activeforeground="#1e3a8a",
            relief="flat",
            bd=0,
            padx=12,
            pady=3,
            font=ui_font(9, bold=True),
            cursor="hand2",
        )
        self.lang_btn.pack(side="right")
        self.help_btn = tk.Button(
            title_row,
            text=t("help"),
            command=self.toggle_help,
            bg="#fbbf24",
            fg="#7c2d12",
            activebackground="#f59e0b",
            activeforeground="#7c2d12",
            relief="flat",
            bd=0,
            padx=12,
            pady=3,
            font=ui_font(9, bold=True),
            cursor="hand2",
        )
        self.help_btn.pack(side="right", padx=(0, 8))
        tk.Label(
            title_row,
            text=t("app_name"),
            fg="white",
            bg="#1d4ed8",
            font=ui_font(14, bold=True),
            anchor="w",
        ).pack(side="left")
        self.header_hint = tk.Label(
            header,
            text=t("header_hint"),
            fg="#dbeafe",
            bg="#1d4ed8",
            font=ui_font(8),
            wraplength=560,
            justify="left",
            anchor="w",
        )
        self.header_hint.pack(fill="x", padx=12, pady=(2, 8))
        self.help_panel = tk.Label(
            header,
            text=t("help_text"),
            bg="#fff7ed",
            fg="#9a3412",
            font=ui_font(9),
            justify="left",
            anchor="w",
            wraplength=560,
            padx=12,
            pady=8,
        )

        body = tk.Frame(main, bg="#f3f6fb")
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        self.status = tk.Label(
            body,
            text=t("scanning"),
            bg="#e0e7ff",
            fg="#1e3a8a",
            font=ui_font(9),
            anchor="w",
            justify="left",
            padx=8,
            pady=4,
        )
        self.status.grid(row=0, column=0, sticky="ew")

        list_wrap = tk.LabelFrame(
            body,
            text=t("pick_user"),
            bg="#f3f6fb",
            font=ui_font(9, bold=True),
        )
        list_wrap.grid(row=1, column=0, sticky="nsew", pady=(6, 4))
        list_wrap.columnconfigure(0, weight=1)
        list_wrap.rowconfigure(1, weight=1)

        search_row = tk.Frame(list_wrap, bg="#f3f6fb")
        search_row.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 0))
        tk.Label(
            search_row,
            text=t("search_users"),
            bg="#f3f6fb",
            font=ui_font(9),
        ).pack(side="left")
        ttk.Entry(search_row, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=(8, 0))

        list_box = tk.Frame(list_wrap, bg="#ffffff")
        list_box.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        list_box.columnconfigure(0, weight=1)
        list_box.rowconfigure(0, weight=1)
        canvas = tk.Canvas(list_box, bg="#ffffff", highlightthickness=0)
        scroll = ttk.Scrollbar(list_box, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas, bg="#ffffff")
        self.list_frame.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        self._list_window = canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(self._list_window, width=event.width))

        def on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        self.progress = tk.Label(
            body,
            text=t("progress_hint"),
            bg="#f8fafc",
            fg="#334155",
            font=ui_font(9),
            anchor="w",
            padx=8,
            pady=4,
        )
        self.progress.grid(row=2, column=0, sticky="ew")

        gain_row = tk.Frame(body, bg="#f3f6fb")
        gain_row.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        tk.Label(
            gain_row,
            text=t("gain"),
            bg="#f3f6fb",
            font=ui_font(9),
        ).pack(side="left")
        self.gain_label = tk.Label(
            gain_row,
            text=f"{self.gain_var.get()}%",
            bg="#f3f6fb",
            font=ui_font(9, bold=True),
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
        buttons.grid(row=4, column=0, sticky="ew", pady=4)
        ttk.Button(buttons, text=t("refresh"), command=self.refresh).pack(side="left")
        self.autostart_btn = ttk.Button(buttons, text=t("autostart_off"), command=self.toggle_autostart)
        self.autostart_btn.pack(side="left", padx=6)
        self._refresh_autostart_button()
        ttk.Button(buttons, text=t("boost_volume"), command=self.boost_volume).pack(side="left")
        self.off_btn = ttk.Button(buttons, text=t("close_restore"), command=lambda: self.apply(False))
        self.on_btn = ttk.Button(buttons, text=t("open_fix"), command=lambda: self.apply(True))
        self.off_btn.pack(side="right")
        self.on_btn.pack(side="right", padx=6)

        self.log = tk.Text(
            body,
            height=4,
            wrap="word",
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
        )
        self.log.grid(row=5, column=0, sticky="ew")
        self.log.insert("1.0", t("log_must_open") + "\n")
        self.log.insert("end", t("log_no_icon") + "\n")
        self.log.insert("end", t("log_one_user") + "\n")
        self.log.configure(state="disabled")
        self._refresh_sidebar()

    def toggle_help(self) -> None:
        self._help_open = not self._help_open
        if self._help_open:
            self.help_panel.pack(fill="x")
            self.help_btn.configure(text=t("hide_help"))
        else:
            self.help_panel.pack_forget()
            self.help_btn.configure(text=t("help"))

    def _show_language_menu(self) -> None:
        menu = tk.Menu(self, tearoff=0)
        for code in SUPPORTED:
            label = LANGUAGE_NAMES[code]
            if code == current_language():
                label = f"✓ {label}"
            menu.add_command(label=label, command=lambda item=code: self._change_language(item))
        try:
            menu.tk_popup(
                self.lang_btn.winfo_rootx(),
                self.lang_btn.winfo_rooty() + self.lang_btn.winfo_height(),
            )
        finally:
            menu.grab_release()

    def _change_language(self, code: str) -> None:
        if code not in SUPPORTED or code == current_language():
            return
        help_open = self._help_open
        set_language(code)
        save_ui_state(language=code)
        for child in self.winfo_children():
            child.destroy()
        self.title(t("window_title"))
        self._help_open = False
        self._build()
        if help_open:
            self.toggle_help()
        if self.profiles:
            self._paint_list()
            self._on_choice()

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

    def selected_profiles(self):
        wanted = set(self.checked_keys)
        return [item for item in self.profiles if item.key in wanted]

    def selected_profile(self):
        items = self.selected_profiles()
        return items[0] if items else None

    def refresh(self) -> None:
        if self.busy or self._refreshing:
            return
        self._refreshing = True
        last = set(self.checked_keys)
        self.status.configure(text=t("scanning"), bg="#e0e7ff", fg="#1e3a8a")

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
        self.status.configure(text=t("scan_failed", error=exc), bg="#fef2f2", fg="#991b1b")

    def _render_profiles(self, profiles, snapshot, last: set[str]) -> None:
        self._refreshing = False
        self.profiles = profiles
        self._snapshot = snapshot
        self.installs = [item for item, _running, _fixed, _items in snapshot]
        if self.busy:
            return
        if not profiles:
            self.checked_keys = set()
            self._paint_list()
            self.status.configure(text=t("no_browsers"), bg="#fef3c7", fg="#92400e")
            return

        keys = {item.key for item in profiles}
        remembered = set(last)
        if not remembered:
            raw = load_ui_state().get("profile_keys")
            if isinstance(raw, list):
                remembered = {str(item) for item in raw}
            else:
                one = str(load_ui_state().get("profile_key") or "")
                if one:
                    remembered = {one}
        remembered &= keys
        if not remembered:
            target = default_profile(profiles)
            if target:
                remembered = {target.key}
            elif profiles:
                remembered = {profiles[0].key}
        self.checked_keys = remembered
        self._refresh_sidebar()
        self._paint_list()
        self._on_choice()

    def _on_root_resize(self, event) -> None:
        if event.widget is not self:
            return
        wrap = max(260, event.width - 190)
        if hasattr(self, "header_hint"):
            self.header_hint.configure(wraplength=wrap)
        if hasattr(self, "help_panel"):
            self.help_panel.configure(wraplength=wrap)

    def _category_counts(self) -> dict[str, int]:
        counts = {ALL: len(self.profiles)}
        for name in category_names():
            counts[name] = 0
        for item in self.profiles:
            name = category_of(item.key)
            counts[name] = counts.get(name, 0) + 1
        return counts

    def _browser_names(self) -> list[str]:
        return sorted({item.browser for item in self.profiles if item.browser})

    def _browser_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.profiles:
            counts[item.browser] = counts.get(item.browser, 0) + 1
        return counts

    def _nav_heading(self, text: str) -> None:
        tk.Label(
            self.sidebar_items,
            text=text,
            bg="#eef2f7",
            fg="#64748b",
            font=ui_font(8, bold=True),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(6, 1))

    def _nav_row(self, name: str, count: int, selected: bool, kind: str, label: str | None = None) -> None:
        shown = label if label is not None else name
        row = tk.Frame(self.sidebar_items, bg="#dbeafe" if selected else "#eef2f7")
        row.pack(fill="x", pady=1)
        title = tk.Label(
            row,
            text=shown,
            bg="#dbeafe" if selected else "#eef2f7",
            fg="#1d4ed8" if selected else "#334155",
            font=ui_font(9, bold=selected),
            anchor="w",
            padx=8,
            pady=4,
        )
        title.pack(side="left", fill="x", expand=True)
        badge = tk.Label(
            row,
            text=str(count),
            bg="#dbeafe" if selected else "#eef2f7",
            fg="#64748b",
            font=ui_font(8),
            padx=8,
        )
        badge.pack(side="right")
        for widget in (row, title, badge):
            widget.bind("<Button-1>", lambda _event, item=name, item_kind=kind: self._select_sidebar(item, item_kind))

    def _refresh_sidebar(self) -> None:
        if not hasattr(self, "sidebar_items"):
            return
        options = filter_options()
        current = self.category_filter.get() if self.category_filter.get() in options else ALL
        self.category_filter.set(current)
        if self.nav_kind == "browser" and self.browser_filter not in self._browser_names():
            self.nav_kind = "category"
            self.browser_filter = ""
        for child in self.sidebar_items.winfo_children():
            child.destroy()
        self._nav_heading(t("user_categories"))
        counts = self._category_counts()
        for name in options:
            selected = self.nav_kind == "category" and name == current
            self._nav_row(name, counts.get(name, 0), selected, "category", category_label(name))
        browsers = self._browser_names()
        if browsers:
            self._nav_heading(t("browsers"))
            browser_counts = self._browser_counts()
            for name in browsers:
                selected = self.nav_kind == "browser" and self.browser_filter == name
                self._nav_row(name, browser_counts.get(name, 0), selected, "browser")

    def _select_sidebar(self, name: str, kind: str = "category") -> None:
        self.nav_kind = kind
        if kind == "browser":
            self.browser_filter = name
            self.category_filter.set(ALL)
        else:
            self.browser_filter = ""
            self.category_filter.set(name)
        self._refresh_sidebar()
        self._paint_list()

    def _assign_category(self, key: str, name: str) -> None:
        if self._painting:
            return
        set_category(key, name)
        self._refresh_sidebar()
        self.after(1, self._paint_list)

    def create_category(self) -> None:
        name = simpledialog.askstring(t("new_category"), t("category_name"), parent=self)
        if name is None:
            return
        try:
            label = add_category(name)
        except ValueError as exc:
            messagebox.showwarning(t("new_category"), str(exc))
            return
        self.nav_kind = "category"
        self.browser_filter = ""
        self.category_filter.set(label)
        self._refresh_sidebar()
        self._paint_list()

    def rename_sidebar_category(self) -> None:
        if self.nav_kind != "category":
            messagebox.showinfo(t("rename"), t("rename_pick_user_cat"))
            return
        current = self.category_filter.get() or ALL
        if current in {ALL, UNCATEGORIZED}:
            messagebox.showinfo(t("rename"), t("rename_reserved"))
            return
        name = simpledialog.askstring(t("rename_category"), t("new_name"), initialvalue=current, parent=self)
        if name is None:
            return
        try:
            label = rename_category(current, name)
        except ValueError as exc:
            messagebox.showwarning(t("rename"), str(exc))
            return
        self.nav_kind = "category"
        self.browser_filter = ""
        self.category_filter.set(label)
        self._refresh_sidebar()
        self._paint_list()

    def delete_sidebar_category(self) -> None:
        if self.nav_kind != "category":
            messagebox.showinfo(t("delete_category"), t("delete_pick_user_cat"))
            return
        current = self.category_filter.get() or ALL
        if current in {ALL, UNCATEGORIZED}:
            messagebox.showinfo(t("delete_category"), t("delete_reserved"))
            return
        if not messagebox.askyesno(t("delete_category"), t("delete_confirm", name=current)):
            return
        delete_category(current)
        self.nav_kind = "category"
        self.browser_filter = ""
        self.category_filter.set(ALL)
        self._refresh_sidebar()
        self._paint_list()

    def _visible_profiles(self):
        matched = filter_profiles_by_name(self.profiles, self.search_var.get(), extras=assignments())
        if self.nav_kind == "browser" and self.browser_filter:
            return [item for item in matched if item.browser == self.browser_filter]
        current = self.category_filter.get() or ALL
        if current != ALL:
            matched = [item for item in matched if category_of(item.key) == current]
        return matched

    def _paint_list(self) -> None:
        if self.busy or not hasattr(self, "list_frame"):
            return
        self._painting = True
        try:
            self._refresh_sidebar()
            for child in self.list_frame.winfo_children():
                child.destroy()
            self._cat_vars = []
            self._check_vars = []
            if not self.profiles:
                tk.Label(
                    self.list_frame,
                    text=t("no_browser_found"),
                    bg="#ffffff",
                    fg="#64748b",
                    font=ui_font(9),
                ).pack(anchor="w")
                return

            visible_keys = {item.key for item in self._visible_profiles()}
            shown = 0
            names = category_names()
            for install, running, fixed, items in self._snapshot:
                keep = [item for item in items if item.key in visible_keys]
                if not keep:
                    continue
                tk.Label(
                    self.list_frame,
                    text=t(
                        "install_status",
                        browser=install.browser,
                        run=t("running") if running else t("not_running"),
                        fix=t("fixed") if fixed else t("not_fixed"),
                    ),
                    bg="#ffffff",
                    fg="#1d4ed8",
                    font=ui_font(9, bold=True),
                    anchor="w",
                ).pack(fill="x", pady=(8, 2))
                for item in keep:
                    bits = []
                    bits.append(t("running") if item.selected else t("not_running"))
                    bits.append(t("fixed") if fixed else t("not_fixed"))
                    extra = f"（{' · '.join(bits)}）" if bits else ""
                    row = tk.Frame(self.list_frame, bg="#ffffff")
                    row.pack(fill="x", pady=1)
                    checked = tk.BooleanVar(value=item.key in self.checked_keys)
                    self._check_vars.append(checked)
                    ttk.Checkbutton(
                        row,
                        text=f"{item.display_name}{extra}",
                        variable=checked,
                        command=lambda key=item.key, var=checked: self._toggle_key(key, var),
                    ).pack(side="left", anchor="w")
                    var = tk.StringVar(value=category_label(category_of(item.key)))
                    self._cat_vars.append(var)
                    combo = ttk.Combobox(
                        row,
                        textvariable=var,
                        values=[category_label(n) for n in names],
                        state="readonly",
                        width=8,
                    )
                    combo.pack(side="left", padx=(8, 0))
                    combo.bind(
                        "<<ComboboxSelected>>",
                        lambda _event, key=item.key, box=var, opts=names: self._assign_category(
                            key, category_from_label(box.get(), opts)
                        ),
                    )
                    shown += 1
            if shown == 0:
                tk.Label(
                    self.list_frame,
                    text=t("no_matching_users"),
                    bg="#ffffff",
                    fg="#64748b",
                    font=ui_font(9),
                ).pack(anchor="w", pady=8)
        finally:
            self._painting = False

    def _toggle_key(self, key: str, var: tk.BooleanVar) -> None:
        if var.get():
            self.checked_keys.add(key)
        else:
            self.checked_keys.discard(key)
        self._on_choice()

    def _on_choice(self) -> None:
        selected = self.selected_profiles()
        if not selected:
            save_ui_state(profile_keys=[], gain_percent=int(self.gain_var.get()))
            self.status.configure(text=t("pick_a_user"), bg="#fef2f2", fg="#991b1b")
            self._set_progress(t("pick_a_user"))
            return
        labels = _join_names([item.label for item in selected])
        save_ui_state(
            user_data=selected[0].user_data,
            profile_keys=[item.key for item in selected],
            gain_percent=int(self.gain_var.get()),
        )
        selected_keys = {item.key for item in selected}
        selected_data = {item.user_data for item in selected}
        others = sorted(
            {
                item.browser
                for item in self.profiles
                if item.selected and item.key not in selected_keys and item.user_data not in selected_data
            }
        )
        stay = t("others_idle", names=_join_names(others)) if others else ""
        self.status.configure(
            text=t("current_user", label=labels, stay=stay),
            bg="#ecfdf3",
            fg="#166534",
        )
        self._set_progress(t("click_open", label=labels))

    def _on_gain(self, _value=None) -> None:
        value = int(round(float(self.gain_var.get()) / 25) * 25)
        value = max(100, min(400, value))
        if value != int(self.gain_var.get()):
            self.gain_var.set(value)
        self.gain_label.configure(text=f"{value}%")
        save_ui_state(gain_percent=value)

    def _refresh_autostart_button(self) -> None:
        on = is_autostart_on()
        self.autostart_btn.configure(text=t("autostart_on") if on else t("autostart_off"))

    def toggle_autostart(self) -> None:
        want = not is_autostart_on()
        ok = set_autostart(want)
        self._refresh_autostart_button()
        if not ok:
            messagebox.showerror(t("autostart"), t("autostart_fail"))
            return
        self._set_progress(
            t("autostart_enabled") if want else t("autostart_disabled"),
            ok=True,
        )

    def boost_volume(self) -> None:
        selected = self.selected_profiles()
        if not selected:
            messagebox.showwarning(t("not_selected"), t("pick_a_user"))
            return
        exe_paths = {str(item.exe) for item in selected}
        browsers = _join_names(sorted({item.browser for item in selected}))

        def work() -> None:
            changed = set_browser_volume(1.0, exe_paths=exe_paths)
            self.after(
                0,
                lambda: self._set_progress(
                    t("volume_ok", browser=browsers, count=changed),
                    ok=True,
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def apply(self, enabled: bool) -> None:
        if self.busy:
            return
        selected = self.selected_profiles()
        if not selected:
            messagebox.showwarning(t("not_selected"), t("pick_a_user"))
            return
        gain = max(1.0, min(4.0, int(self.gain_var.get()) / 100))
        labels = _join_names([item.label for item in selected])
        relaunch = True if enabled else any(item.selected for item in selected)
        self.busy = True
        self.on_btn.configure(state="disabled")
        self.off_btn.configure(state="disabled")
        self._set_progress(t("opening", label=labels))

        def work() -> None:
            report = apply_fix(
                selected,
                enabled=enabled,
                close_first=True,
                relaunch=relaunch,
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
            self._set_progress(t("not_done"), ok=False)
            messagebox.showerror(t("not_done"), "\n".join(report.errors[:6]), parent=self)
            return
        self._set_progress(t("done_open") if enabled else t("done_close"), ok=True)


def hide_console() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass


def main() -> None:
    hide_console()
    try:
        app = App()
        app.mainloop()
    except Exception:
        ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
        ERROR_PATH.write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
