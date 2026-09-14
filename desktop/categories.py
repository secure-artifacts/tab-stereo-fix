"""User-defined categories for browser profiles. Does not change fix logic."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from desktop.i18n import t
    from desktop.paths import config_file
except ImportError:  # pragma: no cover
    from i18n import t
    from paths import config_file

UNCATEGORIZED = "未分类"
ALL = "全部"
PRESETS = (UNCATEGORIZED, "工作", "个人")
STORE = config_file("user-categories.json")


def _empty() -> dict:
    return {"names": list(PRESETS), "assign": {}}


def load_store() -> dict:
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    names = [str(item).strip() for item in data.get("names") or PRESETS if str(item).strip()]
    if UNCATEGORIZED not in names:
        names.insert(0, UNCATEGORIZED)
    assign = data.get("assign") or {}
    if not isinstance(assign, dict):
        assign = {}
    cleaned = {str(key): str(value).strip() or UNCATEGORIZED for key, value in assign.items() if str(key)}
    return {"names": names, "assign": cleaned}


def save_store(data: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def category_names() -> list[str]:
    names = load_store()["names"]
    extra = [name for name in load_store()["assign"].values() if name and name not in names]
    return names + extra


def category_of(profile_key: str) -> str:
    name = load_store()["assign"].get(profile_key) or UNCATEGORIZED
    return name if name else UNCATEGORIZED


def set_category(profile_key: str, name: str) -> str:
    label = (name or UNCATEGORIZED).strip() or UNCATEGORIZED
    data = load_store()
    if label not in data["names"]:
        data["names"].append(label)
    data["assign"][profile_key] = label
    save_store(data)
    return label


def add_category(name: str) -> str:
    label = (name or "").strip()
    if not label:
        raise ValueError(t("empty_category"))
    if label == ALL:
        raise ValueError(t("bad_category_name"))
    data = load_store()
    if label not in data["names"]:
        data["names"].append(label)
        save_store(data)
    return label


def rename_category(old: str, new: str) -> str:
    source = (old or "").strip()
    label = (new or "").strip()
    if source in {ALL, UNCATEGORIZED}:
        raise ValueError(t("cannot_rename"))
    if not label:
        raise ValueError(t("empty_category"))
    if label in {ALL, UNCATEGORIZED}:
        raise ValueError(t("bad_category_name"))
    data = load_store()
    if source not in data["names"] and source not in data["assign"].values():
        raise ValueError(t("no_such_category"))
    if label != source and label in data["names"]:
        raise ValueError(t("category_exists"))
    data["names"] = [label if item == source else item for item in data["names"]]
    if label not in data["names"]:
        data["names"].append(label)
    data["assign"] = {key: (label if value == source else value) for key, value in data["assign"].items()}
    save_store(data)
    return label


def delete_category(name: str) -> None:
    label = (name or "").strip()
    if not label or label in {ALL, UNCATEGORIZED}:
        return
    data = load_store()
    data["names"] = [item for item in data["names"] if item != label]
    data["assign"] = {
        key: (UNCATEGORIZED if value == label else value) for key, value in data["assign"].items()
    }
    save_store(data)


def filter_options() -> list[str]:
    return [ALL, *category_names()]


def assignments() -> dict[str, str]:
    return dict(load_store()["assign"])
