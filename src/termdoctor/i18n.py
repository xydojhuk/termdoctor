from __future__ import annotations

import json
import os
from contextvars import ContextVar
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_LOCALES = {"en": "English", "ru": "Русский"}
LOCALE_ALIASES = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "ru": "ru",
    "rus": "ru",
    "russian": "ru",
    "рус": "ru",
    "русский": "ru",
}
CONFIG_DIR = Path.home() / ".termdoctor"
CONFIG_FILE = CONFIG_DIR / "config.json"
_current_locale: ContextVar[str] = ContextVar("termdoctor_locale", default="en")
_catalog_cache: dict[str, dict[str, Any]] = {}


def normalize_locale(value: str | None) -> str:
    if not value:
        return "en"
    normalized = value.strip().lower().replace("_", "-")
    normalized = normalized.split("-", 1)[0]
    locale = LOCALE_ALIASES.get(normalized)
    if locale is None:
        supported = ", ".join(sorted(SUPPORTED_LOCALES))
        raise ValueError(f"Unsupported language '{value}'. Supported languages: {supported}.")
    return locale


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(CONFIG_FILE)


def set_saved_locale(value: str) -> str:
    locale = normalize_locale(value)
    config = load_config()
    config["language"] = locale
    save_config(config)
    return locale


def resolve_locale(explicit: str | None = None) -> str:
    if explicit:
        return normalize_locale(explicit)

    env_locale = os.environ.get("TERMDOCTOR_LANG")
    if env_locale:
        try:
            return normalize_locale(env_locale)
        except ValueError:
            pass

    saved_locale = load_config().get("language")
    if isinstance(saved_locale, str):
        try:
            return normalize_locale(saved_locale)
        except ValueError:
            pass

    system_locale = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG")
    if system_locale:
        try:
            return normalize_locale(system_locale)
        except ValueError:
            pass

    return "en"


def set_locale(value: str | None = None) -> str:
    locale = resolve_locale(value)
    _current_locale.set(locale)
    return locale


def get_locale() -> str:
    return _current_locale.get()


def _load_catalog(locale: str) -> dict[str, Any]:
    if locale in _catalog_cache:
        return _catalog_cache[locale]

    catalog_file = resources.files("termdoctor").joinpath(f"locales/{locale}.yml")
    with catalog_file.open("r", encoding="utf-8") as file:
        catalog = yaml.safe_load(file) or {}
    _catalog_cache[locale] = catalog
    return catalog


def _lookup(catalog: dict[str, Any], key: str) -> Any:
    current: Any = catalog
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def tr(key: str, locale: str | None = None, **params: Any) -> str:
    selected = normalize_locale(locale) if locale else get_locale()
    value = _lookup(_load_catalog(selected), key)
    if value is None and selected != "en":
        value = _lookup(_load_catalog("en"), key)
    if value is None:
        value = key
    if not isinstance(value, str):
        return str(value)
    try:
        return value.format(**params)
    except (KeyError, ValueError):
        return value


def history_enabled() -> bool:
    """History is opt-in; old history files are never deleted automatically."""
    return load_config().get("history_enabled") is True


def save_history_enabled(value: bool) -> None:
    config = load_config()
    config["history_enabled"] = value
    save_config(config)
