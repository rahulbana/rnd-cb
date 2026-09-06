"""In-memory fake vector store with cosine similarity search.

Namespaced by org, mirroring the multi-tenant hook every real store exposes.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.models import Chunk, EmbeddingVector, RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class FakeVectorStore:
    """Process-local vector store; state lives in a dict keyed by namespace."""

    name = "fake"

    def __init__(self) -> None:
        # namespace -> chunk_id -> (Chunk, vector values)
        self._data: dict[str, dict[str, tuple[Chunk, list[float]]]] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeVectorStore:
        return cls()

    async def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[EmbeddingVector],
        *,
        namespace: str,
    ) -> None:
        bucket = self._data.setdefault(namespace, {})
        for chunk, vec in zip(chunks, vectors, strict=False):
            bucket[chunk.id] = (chunk, list(vec.values))

    async def search(
        self,
        query: EmbeddingVector,
        *,
        namespace: str,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        bucket = self._data.get(namespace, {})
        scored = [
            RetrievedChunk(
                chunk=chunk,
                score=_cosine(query.values, values),
                source="dense",
            )
            for chunk, values in bucket.values()
        ]
        scored.sort(key=lambda rc: rc.score, reverse=True)
        return scored[:top_k]

    async def delete(self, chunk_ids: Sequence[str], *, namespace: str) -> None:
        bucket = self._data.get(namespace, {})
        for cid in chunk_ids:
            bucket.pop(cid, None)
