"""Central tool registry (spec section 20)."""
from __future__ import annotations

from typing import Any

from ..config.logging import get_logger
from .base import Tool, ToolResult

logger = get_logger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> list[dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool with defensive error handling (spec section 26)."""
        try:
            tool = self.get(name)
        except KeyError as exc:
            return ToolResult(tool=name, ok=False, error=str(exc))
        try:
            return await tool.run(**kwargs)
        except Exception as exc:  # graceful degradation — never crash an agent
            logger.warning("tool %s failed: %s", name, exc)
            return ToolResult(tool=name, ok=False, error=str(exc))


def build_default_registry() -> ToolRegistry:
    """Wire up the built-in tools."""
    from .currency import CurrencyTool
    from .flights import FlightSearchTool
    from .geocode import GeocodeTool
    from .places import PlacesTool
    from .search import WebSearchTool
    from .weather import WeatherTool

    registry = ToolRegistry()
    for tool in (WeatherTool(), GeocodeTool(), CurrencyTool(), WebSearchTool(),
                 FlightSearchTool(), PlacesTool()):
        registry.register(tool)
    return registry
