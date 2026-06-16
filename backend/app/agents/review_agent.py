"""Review agent: extracts and categorizes reviews from many source types."""

from __future__ import annotations

from typing import Any

from ..llm import LLMClient
from ..models import Review, ReviewerType, SearchResult, Sentiment
from ._helpers import format_sources

SYSTEM = (
    "You are a review-aggregation specialist. From the provided web sources, "
    "extract distinct reviews/opinions about the book and attribute each to its "
    "source. Classify each reviewer as one of: reader, critic, company, "
    "celebrity, unknown. Capture sentiment (positive, mixed, negative, unknown) "
    "and a short verbatim-style excerpt. Only use information present in the "
    "sources; do not fabricate reviewers. Respond with a single JSON object."
)


class ReviewAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def run(self, title: str, sources: list[SearchResult]) -> list[Review]:
        context = format_sources(sources)
        user = (
            f"Book title: {title}\n\n"
            f"Sources:\n{context}\n\n"
            "Return JSON with key 'reviews' = array of objects, each with keys: "
            "reviewer_name (string), reviewer_type (reader|critic|company|"
            "celebrity|unknown), source (string, e.g. 'Goodreads'), source_url "
            "(string), rating (number 0-5 or null), sentiment (positive|mixed|"
            "negative|unknown), excerpt (string)."
        )

        def mock() -> dict[str, Any]:
            return {
                "reviews": [
                    {
                        "reviewer_name": "Goodreads readers",
                        "reviewer_type": "reader",
                        "source": "Goodreads",
                        "source_url": "https://www.goodreads.com/book/mock",
                        "rating": 4.2,
                        "sentiment": "positive",
                        "excerpt": "Could not put it down, a stunning read.",
                    },
                    {
                        "reviewer_name": "The New York Times",
                        "reviewer_type": "critic",
                        "source": "The New York Times",
                        "source_url": "https://www.nytimes.com/mock-review",
                        "rating": None,
                        "sentiment": "mixed",
                        "excerpt": "Ambitious and deeply human, though the middle act drags.",
                    },
                    {
                        "reviewer_name": "Oprah Winfrey",
                        "reviewer_type": "celebrity",
                        "source": "Oprah's Book Club",
                        "source_url": "https://oprah.com/mock",
                        "rating": None,
                        "sentiment": "positive",
                        "excerpt": "It stayed with me for weeks.",
                    },
                ]
            }

        data = self.llm.complete_json(system=SYSTEM, user=user, mock=mock)
        return [_to_review(item) for item in (data.get("reviews") or [])]


def _to_review(item: dict[str, Any]) -> Review:
    return Review(
        reviewer_name=str(item.get("reviewer_name") or "Unknown"),
        reviewer_type=_enum(ReviewerType, item.get("reviewer_type"), ReviewerType.unknown),
        source=str(item.get("source") or ""),
        source_url=str(item.get("source_url") or ""),
        rating=_to_float(item.get("rating")),
        sentiment=_enum(Sentiment, item.get("sentiment"), Sentiment.unknown),
        excerpt=str(item.get("excerpt") or ""),
    )


def _enum(enum_cls, value, default):
    try:
        return enum_cls(str(value).lower())
    except (ValueError, AttributeError):
        return default


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
