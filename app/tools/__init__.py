"""Tool package — assembles every tool into a single registry."""

from __future__ import annotations

from . import (
    calculator,
    database,
    deep_search,
    email_tool,
    filesystem,
    shell,
    web_search,
)
from .base import Tool, ToolRegistry

# Order here controls the order tools are advertised to the model.
_MODULES = [
    database,
    web_search,
    deep_search,
    filesystem,
    email_tool,
    calculator,
    shell,
]


def build_registry(config) -> ToolRegistry:
    registry = ToolRegistry()
    for module in _MODULES:
        module.register(registry, config)
    return registry


__all__ = ["Tool", "ToolRegistry", "build_registry"]
