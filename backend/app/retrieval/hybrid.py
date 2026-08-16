"""Hybrid retrieval: dense vectors + sparse BM25 keyword search, fused.

Vector search captures semantic similarity; BM25 captures exact term/keyword
matches (names, codes, acronyms) that embeddings often miss. Results are
combined with Reciprocal Rank Fusion (RRF), which is robust because it fuses on
rank rather than trying to calibrate incomparable score scales, weighted by
``hybrid_alpha``.

The BM25 index is built from the vector store's documents and cached; it is
rebuilt when the store's chunk count changes (i.e. after new ingestion).
"""
from __future__ import annotations

import re
import threading

from .base import BaseRetriever, RetrievedChunk
from .simple import SimpleRetriever
from ..config import get_settings
from ..core.logging import get_logger
from ..vectorstore import get_vectorstore

log = get_logger(__name__)

_RRF_K = 60  # standard RRF damping constant


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class _BM25Index:
    """Lazily-built, count-invalidated BM25 index over all stored chunks."""

    def __init__(self) -> None:
        self._bm25 = None
        self._docs: list = []
        self._built_count = -1
        self._lock = threading.Lock()

    def _ensure(self) -> None:
        store = get_vectorstore()
        count = store.count()
        if self._bm25 is not None and count == self._built_count:
            return
        with self._lock:
            if self._bm25 is not None and count == self._built_count:
                return
            from rank_bm25 import BM25Okapi
            docs = store.all_documents()
            corpus = [_tokenize(d.text) for d in docs] or [[""]]
            self._bm25 = BM25Okapi(corpus)
            self._docs = docs
            self._built_count = count
            log.info("Built BM25 index over %d chunks", len(docs))

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        self._ensure()
        if not self._docs:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        out = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            d = self._docs[i]
            out.append(RetrievedChunk(id=d.id, text=d.text, metadata=d.metadata,
                                      score=float(scores[i]),
                                      scores={"bm25": float(scores[i])}))
        return out


_bm25_index = _BM25Index()


class HybridRetriever(BaseRetriever):
    name = "hybrid"

    def __init__(self) -> None:
        self._dense = SimpleRetriever()

    def retrieve(self, query: str, top_k: int,
                 query_embedding: list[float] | None = None) -> list[RetrievedChunk]:
        alpha = get_settings().hybrid_alpha
        # Over-fetch from each arm so fusion has candidates to work with.
        dense = self._dense.retrieve(query, top_k, query_embedding)
        sparse = _bm25_index.search(query, top_k=top_k)

        fused: dict[str, RetrievedChunk] = {}
        rrf: dict[str, float] = {}

        for rank, chunk in enumerate(dense):
            rrf[chunk.id] = rrf.get(chunk.id, 0.0) + alpha * (1.0 / (_RRF_K + rank + 1))
            fused.setdefault(chunk.id, chunk).scores.update(chunk.scores)
        for rank, chunk in enumerate(sparse):
            rrf[chunk.id] = rrf.get(chunk.id, 0.0) + (1 - alpha) * (1.0 / (_RRF_K + rank + 1))
            existing = fused.setdefault(chunk.id, chunk)
            existing.scores.update(chunk.scores)

        for cid, score in rrf.items():
            fused[cid].score = score
            fused[cid].scores["rrf"] = score

        ordered = sorted(fused.values(), key=lambda c: c.score, reverse=True)
        return ordered[:top_k]
