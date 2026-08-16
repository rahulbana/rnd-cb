"""Retrieval interface and shared result type."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedChunk:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    # Component scores kept for observability / debugging in the UI.
    scores: dict[str, float] = field(default_factory=dict)


class BaseRetriever(ABC):
    name: str = "base"

    @abstractmethod
    def retrieve(self, query: str, top_k: int,
                 query_embedding: list[float] | None = None) -> list[RetrievedChunk]:
        """Retrieve candidates. ``query_embedding`` may be supplied to reuse a
        precomputed vector (so embedding can be timed as its own pipeline step
        instead of being hidden inside retrieval)."""
