"""Web search tool (stub).

Returns an explicit "no live index" result offline so agents never fabricate
citations. Wire a real search API in behind this interface for production.
External results, when present, must be treated as untrusted (spec section 28).
"""
from __future__ import annotations

from .base import Tool, ToolResult


class WebSearchTool(Tool):
    name = "search"
    description = "Search the web for travel information (returns untrusted external content)."

    async def run(self, *, query: str, **_: object) -> ToolResult:
        # No live search backend is configured in this build. We return an
        # honest empty result rather than inventing sources.
        return ToolResult(
            tool=self.name,
            ok=True,
            source="none",
            data={"query": query, "results": [], "note": "no live search backend configured"},
        )
