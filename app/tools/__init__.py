"""Tool registry: discovers and aggregates every tool module.

Each tool module exposes a `get_tools() -> list[Tool]` function. To add a new
capability, create a module here and add it to `_MODULES`.
"""
from __future__ import annotations

from . import (
    age,
    air_quality,
    country,
    currency,
    festival,
    history_events,
    holidays,
    image_resize,
    llm_tools,
    measurement,
    news,
    notes_tools,
    research_export,
    system_health,
    weather,
    web_search,
)
from .base import Tool

_MODULES = [
    web_search,
    country,
    weather,
    air_quality,
    currency,
    measurement,
    system_health,
    llm_tools,
    research_export,
    notes_tools,
    history_events,
    festival,
    image_resize,
    news,
    holidays,
    age,
]


def get_all_tools() -> list[Tool]:
    """Return every Tool provided by every registered module."""
    tools: list[Tool] = []
    for module in _MODULES:
        tools.extend(module.get_tools())
    return tools


def build_registry() -> dict[str, Tool]:
    """Return a mapping of tool name -> Tool."""
    return {t.name: t for t in get_all_tools()}
