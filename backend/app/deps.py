"""Shared dependencies (singletons) for the API."""
from __future__ import annotations

from functools import lru_cache

from .config import Settings, get_settings
from .services.history import HistoryStore


@lru_cache
def get_history_store() -> HistoryStore:
    settings = get_settings()
    return HistoryStore(settings.history_db_path)


def resolve_dialect(settings: Settings, override: str | None) -> str:
    return (override or settings.sql_dialect or "postgres").strip().lower()
