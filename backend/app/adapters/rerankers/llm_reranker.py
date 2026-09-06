"""LLM-as-reranker -- prompt an LLM to score each candidate's relevance.

Uses the LLMProvider port, so any configured LLM backend can rerank. Slower and
costlier than a cross-encoder; useful when no reranker model is available or for
nuanced relevance. Scores are parsed defensively (a missing/garbled number
falls back to the candidate's incoming score).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.models import ChatMessage, RetrievedChunk, Role

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.domain.interfaces import LLMProvider

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")

_SYSTEM = (
    "You are a search relevance judge. Rate how well the PASSAGE answers the "
    "QUERY on a scale from 0 (irrelevant) to 10 (perfectly relevant). Reply "
    "with only the number."
)


class LLMReranker:
    """Re-scores candidates by asking an LLM to rate each one."""

    name = "llm"

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @classmethod
    def from_settings(cls, settings: Settings) -> LLMReranker:
        from app.core.registry import get_llm_provider

        return cls(get_llm_provider())

    async def _score(self, query: str, text: str, fallback: float) -> float:
        messages = [
            ChatMessage(role=Role.SYSTEM, content=_SYSTEM),
            ChatMessage(role=Role.USER, content=f"QUERY: {query}\nPASSAGE: {text}"),
        ]
        response = await self._llm.generate(messages, temperature=0.0)
        match = _NUMBER_RE.search(response.content)
        return float(match.group(0)) if match else fallback

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        rescored: list[RetrievedChunk] = []
        for candidate in candidates:
            score = await self._score(query, candidate.chunk.text, candidate.score)
            rescored.append(
                RetrievedChunk(chunk=candidate.chunk, score=score, source="reranker")
            )
        rescored.sort(key=lambda rc: rc.score, reverse=True)
        return rescored[:top_k]
