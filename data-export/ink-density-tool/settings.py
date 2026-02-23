"""App settings — persistent key/value store backed by settings.json.

On Windows the settings file lives in %APPDATA%/InkDensityTool/settings.json.
On other platforms it falls back to ~/.ink-density-tool/settings.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


APP_NAME = "InkDensityTool"

_DEFAULTS: dict = {
    "illustrator_path": "",
    "ai_template_1lpi": "",
    "ai_template_2lpi": "",
    "ai_template_3lpi": "",
    "ai_template_1lpi_extended": "",
    "ai_template_2lpi_extended": "",
    "ai_template_3lpi_extended": "",
    "default_weight_labels": ["120#", "150#", "200#"],
    "default_step_labels": [
        "100", "95", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5", "3", "1"
    ],
    "last_session_path": "",
}

_cache: dict | None = None


def _settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home()
    return base / APP_NAME / "settings.json"


def load() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    path = _settings_path()
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                stored = json.load(f)
        except Exception:
            stored = {}
    else:
        stored = {}

    # Merge defaults so new keys are always present
    merged = dict(_DEFAULTS)
    merged.update(stored)
    _cache = merged
    return _cache


def _save(data: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value) -> None:
    data = load()
    data[key] = value
    _save(data)
