"""Web search tool (Tavily)."""

from __future__ import annotations

from langchain_core.tools import tool

from ..config import Settings


def make_web_tools(settings: Settings) -> list:
    @tool
    def web_search(query: str, max_results: int = 5) -> str:
        """Search the web for current, real-world information using Tavily.

        Use for recent events, facts you're unsure about, prices, docs, etc.
        """
        if not settings.tavily_api_key:
            return (
                "Web search is unavailable: TAVILY_API_KEY is not set. "
                "Ask the user to set it to enable web search."
            )
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.tavily_api_key)
            data = client.search(
                query,
                max_results=max(1, min(max_results, 10)),
                include_answer=True,
            )
        except Exception as exc:
            return f"Web search failed: {exc}"

        lines = []
        if data.get("answer"):
            lines.append(f"Answer: {data['answer']}")
        for r in data.get("results", []):
            lines.append(
                f"- {r.get('title')} ({r.get('url')})\n  {r.get('content', '')[:300]}"
            )
        return "\n".join(lines) or "No results found."

    return [web_search]
