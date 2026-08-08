"""Quick web search tool backed by Tavily.

Returns a compact list of titles, URLs, and snippets — enough for the model to
answer a factual question or decide it needs the deep-research tool. The Tavily
client is created lazily and cached so we only import/instantiate it when the
tool is actually used.
"""

from __future__ import annotations

from .base import Tool, ToolRegistry

_client = None


def _get_client(api_key: str):
    global _client
    if _client is None:
        from tavily import TavilyClient

        _client = TavilyClient(api_key=api_key)
    return _client


def register(registry: ToolRegistry, config) -> None:
    def web_search(query: str, max_results: int = 5) -> str:
        if not config.tavily_api_key:
            return (
                "Web search is not configured. Set TAVILY_API_KEY in the "
                "environment to enable it."
            )
        max_results = max(1, min(int(max_results), 10))
        try:
            client = _get_client(config.tavily_api_key)
            resp = client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=True,
            )
        except Exception as exc:  # noqa: BLE001
            return f"Web search failed: {exc}"

        lines = []
        if resp.get("answer"):
            lines.append(f"Quick answer: {resp['answer']}\n")
        for i, r in enumerate(resp.get("results", []), 1):
            lines.append(
                f"{i}. {r.get('title', 'Untitled')}\n"
                f"   {r.get('url', '')}\n"
                f"   {(r.get('content') or '').strip()[:400]}"
            )
        return "\n".join(lines) if lines else "No results found."

    registry.register(
        Tool(
            name="web_search",
            description=(
                "Search the public web for up-to-date information and return a "
                "short list of relevant results with snippets. Use for quick "
                "facts, current prices, product info, or recent news."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {
                        "type": "integer",
                        "description": "How many results to return (1-10, default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=web_search,
        )
    )
