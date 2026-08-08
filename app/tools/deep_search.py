"""Deep web research tool backed by Tavily.

Where ``web_search`` is a quick skim, this runs an advanced search and then
pulls the full extracted content of the top pages so the model can synthesise a
thorough, cited answer. It shares Tavily's client with the quick-search tool
but is a distinct tool so the model chooses depth deliberately (deep research
is slower and costs more).
"""

from __future__ import annotations

from . import web_search as _quick  # reuse the cached Tavily client
from .base import Tool, ToolRegistry


def register(registry: ToolRegistry, config) -> None:
    def deep_web_search(query: str, max_results: int = 5) -> str:
        if not config.tavily_api_key:
            return (
                "Deep web search is not configured. Set TAVILY_API_KEY in the "
                "environment to enable it."
            )
        max_results = max(1, min(int(max_results), 8))
        try:
            client = _quick._get_client(config.tavily_api_key)
            resp = client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer="advanced",
                include_raw_content=True,
            )
        except Exception as exc:  # noqa: BLE001
            return f"Deep web search failed: {exc}"

        sections = []
        if resp.get("answer"):
            sections.append(f"# Synthesised answer\n{resp['answer']}\n")
        sections.append("# Sources")
        for i, r in enumerate(resp.get("results", []), 1):
            body = (r.get("raw_content") or r.get("content") or "").strip()
            if len(body) > 1500:
                body = body[:1500] + " ..."
            sections.append(
                f"\n## [{i}] {r.get('title', 'Untitled')}\n"
                f"URL: {r.get('url', '')}\n"
                f"Relevance score: {r.get('score', 'n/a')}\n\n{body}"
            )
        return "\n".join(sections) if len(sections) > 1 else "No results found."

    registry.register(
        Tool(
            name="deep_web_search",
            description=(
                "Perform in-depth web research: an advanced multi-source search "
                "that also extracts the full page content of top results, for a "
                "thorough, well-sourced answer. Slower than web_search — use it "
                "for comparisons, market research, or questions needing detail "
                "and citations."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The research question."},
                    "max_results": {
                        "type": "integer",
                        "description": "Number of sources to analyse (1-8, default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=deep_web_search,
        )
    )
