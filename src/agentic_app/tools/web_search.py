"""Web search tools: Tavily (keyed, high quality) and DuckDuckGo (keyless).

Both are exposed as OpenAI Agents `function_tool`s. They degrade gracefully:
a missing key or unavailable backend returns a structured error string rather
than raising, so the agent can recover (e.g. fall back to the other engine).
"""

from __future__ import annotations

import json
from typing import Any

from agents import function_tool

from agentic_app.config import get_settings


def _format(results: list[dict[str, Any]], engine: str, query: str) -> str:
    payload = {"engine": engine, "query": query, "results": results}
    return json.dumps(payload, ensure_ascii=False, indent=2)


@function_tool
def web_search_tavily(query: str, max_results: int = 5) -> str:
    """Search the web with Tavily for high-quality, LLM-optimized results.

    Use this for current events, facts, and research questions. Returns a JSON
    string with a list of results (title, url, snippet). Prefer this engine
    when a Tavily API key is configured.

    Args:
        query: The search query.
        max_results: Number of results to return (1-10).
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        return _format(
            [],
            "tavily",
            query,
        ).replace(
            '"results": []',
            '"results": [], "error": "TAVILY_API_KEY not set; use web_search_duckduckgo instead."',
        )
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        max_results = max(1, min(int(max_results), 10))
        resp = client.search(query=query, max_results=max_results)
        results = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": r.get("content"),
                "score": r.get("score"),
            }
            for r in resp.get("results", [])
        ]
        return _format(results, "tavily", query)
    except Exception as exc:  # noqa: BLE001 - surface to the agent, don't crash
        return json.dumps({"engine": "tavily", "query": query, "error": str(exc)})


@function_tool
def web_search_duckduckgo(query: str, max_results: int = 5) -> str:
    """Search the web with DuckDuckGo (no API key required).

    A reliable keyless fallback for general web search. Returns a JSON string
    with a list of results (title, url, snippet).

    Args:
        query: The search query.
        max_results: Number of results to return (1-10).
    """
    try:
        from ddgs import DDGS

        max_results = max(1, min(int(max_results), 10))
        results: list[dict[str, Any]] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title"),
                        "url": r.get("href") or r.get("url"),
                        "snippet": r.get("body"),
                    }
                )
        return _format(results, "duckduckgo", query)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"engine": "duckduckgo", "query": query, "error": str(exc)})
