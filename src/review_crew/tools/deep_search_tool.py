"""Deep web-search tool backed by Tavily.

This tool performs an *advanced* (deep) Tavily search. Advanced search digs
deeper into each page than a normal search, returning richer content snippets
and a relevance score for every result, plus an AI-generated answer. Agents use
it to gather real customer reviews and to verify claims against their sources.
"""

import os
from typing import Type

from pydantic import BaseModel, Field

try:
    # CrewAI >= 0.86 exposes BaseTool here.
    from crewai.tools import BaseTool
except ImportError:  # pragma: no cover - fallback for older crewai_tools layout
    from crewai_tools import BaseTool

from tavily import TavilyClient


class DeepSearchInput(BaseModel):
    """Input schema for the deep search tool."""

    query: str = Field(
        ...,
        description=(
            "The search query. Be specific, e.g. "
            "'Acme Wireless Earbuds customer reviews ratings' or "
            "'Bella Italia restaurant Mumbai reviews complaints'."
        ),
    )
    max_results: int = Field(
        default=8,
        description="How many web results to return (1-15). Defaults to 8.",
    )


class DeepSearchTool(BaseTool):
    name: str = "Deep Web Search"
    description: str = (
        "Performs a DEEP (advanced) web search using Tavily and returns the most "
        "relevant pages. For each result you get the title, the exact source URL, "
        "a rich content snippet, and a relevance score (0-1). The first block is an "
        "AI-generated summary answer. Use this to find real customer reviews, star "
        "ratings, the number of reviewers, and to verify any claim against its "
        "source. ALWAYS keep the source URLs so they can be cited."
    )
    args_schema: Type[BaseModel] = DeepSearchInput

    def _run(self, query: str, max_results: int = 8) -> str:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return (
                "ERROR: TAVILY_API_KEY is not set. Add it to your environment / .env "
                "file so deep search can run."
            )

        max_results = max(1, min(int(max_results), 15))
        client = TavilyClient(api_key=api_key)

        try:
            response = client.search(
                query=query,
                search_depth="advanced",  # <-- the "deep search"
                max_results=max_results,
                include_answer=True,
                include_raw_content=False,
            )
        except Exception as exc:  # noqa: BLE001 - surface the error to the agent
            return f"ERROR: deep search failed for query '{query}': {exc}"

        lines: list[str] = [f"DEEP SEARCH RESULTS FOR: {query}", "=" * 60]

        answer = response.get("answer")
        if answer:
            lines.append("AI SUMMARY ANSWER:")
            lines.append(answer.strip())
            lines.append("-" * 60)

        results = response.get("results", [])
        if not results:
            lines.append("No results found.")
            return "\n".join(lines)

        for i, result in enumerate(results, start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "N/A")
            score = result.get("score", 0.0)
            content = (result.get("content") or "").strip()
            lines.append(f"[{i}] {title}")
            lines.append(f"    SOURCE URL: {url}")
            lines.append(f"    RELEVANCE: {score:.2f}")
            lines.append(f"    CONTENT: {content}")
            lines.append("")

        return "\n".join(lines)
