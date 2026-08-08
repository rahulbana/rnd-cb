"""Application configuration and persistent-settings paths.

Everything user-specific (settings, cached OAuth tokens, provider client
secrets) lives under a per-user config directory so nothing sensitive is ever
written into the project tree.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __app_name__


def _config_root() -> Path:
    """Return the platform-appropriate per-user config directory."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / __app_name__


CONFIG_DIR: Path = _config_root()
TOKENS_DIR: Path = CONFIG_DIR / "tokens"
SETTINGS_FILE: Path = CONFIG_DIR / "settings.json"

# Where users drop their OAuth client credentials. Kept out of source control.
GOOGLE_CLIENT_SECRET_FILE: Path = CONFIG_DIR / "google_client_secret.json"
ONEDRIVE_CONFIG_FILE: Path = CONFIG_DIR / "onedrive_config.json"


def ensure_dirs() -> None:
    """Create the config/token directories if they do not yet exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)


DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "light",          # "light" or "dark"
    "font_family": "Consolas" if sys.platform.startswith("win") else "Monospace",
    "font_size": 11,
    "word_wrap": False,
    "show_whitespace": False,
    "tab_width": 4,
    "use_spaces": True,
    "recent_files": [],        # list of local paths, most-recent first
}


class Settings:
    """A tiny JSON-backed settings store."""

    def __init__(self) -> None:
        ensure_dirs()
        self._data: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                self._data.update(stored)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            # Missing or corrupt settings simply fall back to defaults.
            pass

    def save(self) -> None:
        ensure_dirs()
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def add_recent_file(self, path: str, limit: int = 10) -> None:
        recent = [p for p in self._data.get("recent_files", []) if p != path]
        recent.insert(0, path)
        self._data["recent_files"] = recent[:limit]

    @property
    def data(self) -> dict[str, Any]:
        return self._data
