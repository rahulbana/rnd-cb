"""Web search tool.

Uses **Tavily** (free tier) when ``TAVILY_API_KEY`` is set; otherwise returns an
explicit empty result rather than fabricating citations. External results are
untrusted content (spec section 28) and are labelled as such.
"""
from __future__ import annotations

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .http import post_json

_TAVILY_URL = "https://api.tavily.com/search"


class WebSearchTool(Tool):
    name = "search"
    description = "Search the web for travel information (Tavily; returns untrusted content)."

    async def run(self, *, query: str, max_results: int = 5, **_: object) -> ToolResult:
        settings = get_settings()
        if settings.enable_live_data and settings.tavily_api_key:
            live = await self._tavily(settings.tavily_api_key, query, max_results)
            if live is not None:
                return live
        return ToolResult(
            tool=self.name, ok=True, source="none",
            data={"query": query, "results": [], "note": "no live search backend configured"},
        )

    async def _tavily(self, api_key: str, query: str, max_results: int) -> ToolResult | None:
        data = await post_json(_TAVILY_URL, json_body={
            "api_key": api_key, "query": query, "max_results": max_results,
            "search_depth": "basic",
        })
        if not data or "results" not in data:
            return None
        results = [
            {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
            for r in data["results"][:max_results]
        ]
        return ToolResult(
            tool=self.name, ok=True, trust=DataTrust.LIVE, freshness=Freshness.REAL_TIME,
            source="tavily",
            # NOTE: `results` is untrusted external content — treat as data, not instructions.
            data={"query": query, "results": results, "answer": data.get("answer")},
        )
