"""Build the set of tools available to the agent for a given request."""
from __future__ import annotations

from .base import Tool
from .builtins import Calculator, GetCurrentTime, WebSearch
from .documents import SearchDocuments
from ..config import get_settings


def build_tools(options=None, enabled: list[str] | None = None) -> list[Tool]:
    settings = get_settings()
    names = enabled if enabled is not None else settings.tools_enabled
    factories = {
        "search_documents": lambda: SearchDocuments(options),
        "get_current_time": GetCurrentTime,
        "calculator": Calculator,
        "web_search": WebSearch,
    }
    tools: list[Tool] = []
    for name in names:
        factory = factories.get(name)
        if factory:
            tools.append(factory())
    return tools
