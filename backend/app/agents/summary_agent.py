"""Summary agent: extracts book facts and writes a concise summary."""

from __future__ import annotations

from typing import Any

from ..llm import LLMClient
from ..models import BookInfo, SearchResult
from ._helpers import format_sources

SYSTEM = (
    "You are a meticulous literary research assistant. Using ONLY the provided "
    "web sources, extract factual information about a book and write a neutral, "
    "spoiler-light summary. Never invent facts not supported by the sources. "
    "Respond with a single JSON object."
)


class SummaryAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def run(
        self, title: str, sources: list[SearchResult], author_hint: str | None = None
    ) -> BookInfo:
        context = format_sources(sources)
        user = (
            f"Book title: {title}\n"
            f"Author hint (may be empty): {author_hint or ''}\n\n"
            f"Sources:\n{context}\n\n"
            "Return JSON with keys: title (string), author (string), "
            "published_year (integer or null), genres (array of strings), "
            "summary (string, 3-5 sentences)."
        )

        def mock() -> dict[str, Any]:
            return {
                "title": title,
                "author": author_hint or "Unknown",
                "published_year": None,
                "genres": ["fiction"],
                "summary": (
                    f"{title} is a widely discussed book. This is a placeholder "
                    "summary generated offline because no OPENAI_API_KEY is set."
                ),
            }

        data = self.llm.complete_json(system=SYSTEM, user=user, mock=mock)
        return BookInfo(
            title=str(data.get("title") or title),
            author=str(data.get("author") or author_hint or "Unknown"),
            published_year=_to_int(data.get("published_year")),
            genres=[str(g) for g in (data.get("genres") or [])],
            summary=str(data.get("summary") or ""),
        )


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
