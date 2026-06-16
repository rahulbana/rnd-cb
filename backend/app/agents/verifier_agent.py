"""Verifier agent: sanity-checks the assembled report against the sources."""

from __future__ import annotations

from typing import Any

from ..llm import LLMClient
from ..models import BookInfo, Review, SearchResult, VerificationResult
from ._helpers import format_sources

SYSTEM = (
    "You are a fact-checking / sanity-check agent. You are given a book summary, "
    "a list of extracted reviews, and the original web sources. Determine whether "
    "the summary and reviews are actually supported by the sources. Flag any "
    "claim, reviewer, or rating that is NOT supported by the sources. Be strict "
    "but fair. Respond with a single JSON object."
)


class VerifierAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def run(
        self, book: BookInfo, reviews: list[Review], sources: list[SearchResult]
    ) -> VerificationResult:
        context = format_sources(sources)
        reviews_block = "\n".join(
            f"- {r.reviewer_name} ({r.reviewer_type.value}, {r.sentiment.value}): "
            f"{r.excerpt}"
            for r in reviews
        ) or "(no reviews)"
        user = (
            f"SUMMARY:\nTitle: {book.title}\nAuthor: {book.author}\n"
            f"{book.summary}\n\n"
            f"REVIEWS:\n{reviews_block}\n\n"
            f"SOURCES:\n{context}\n\n"
            "Return JSON with keys: verified (boolean — true if the report is "
            "broadly supported), confidence (number 0-1), notes (string, brief "
            "rationale), flagged_claims (array of strings describing unsupported "
            "or suspicious claims)."
        )

        def mock() -> dict[str, Any]:
            return {
                "verified": True,
                "confidence": 0.5,
                "notes": (
                    "Offline sanity check: report is internally consistent with the "
                    "mock sources. Enable OPENAI_API_KEY for real verification."
                ),
                "flagged_claims": [],
            }

        data = self.llm.complete_json(system=SYSTEM, user=user, mock=mock, temperature=0.0)
        return VerificationResult(
            verified=bool(data.get("verified", False)),
            confidence=_clamp(_to_float(data.get("confidence"))),
            notes=str(data.get("notes") or ""),
            flagged_claims=[str(c) for c in (data.get("flagged_claims") or [])],
        )


def _to_float(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
