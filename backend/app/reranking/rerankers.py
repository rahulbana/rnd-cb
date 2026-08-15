"""Reranker implementations.

  * ``NoOpReranker``       - passthrough (used when reranking is disabled).
  * ``CrossEncoderReranker`` - scores each (query, passage) pair with a
    cross-encoder for far higher precision than bi-encoder retrieval.
  * ``ChainReranker``      - applies multiple rerankers in sequence, each
    narrowing the candidate set (e.g. a fast model then a stronger one).
"""
from __future__ import annotations

from .base import BaseReranker
from ..core.logging import get_logger
from ..retrieval.base import RetrievedChunk

log = get_logger(__name__)


class NoOpReranker(BaseReranker):
    name = "noop"

    def rerank(self, query, chunks, top_k):
        return chunks[:top_k]


class CrossEncoderReranker(BaseReranker):
    name = "cross_encoder"

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def _ensure(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            log.info("Loading reranker: %s", self.model_name)
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query, chunks, top_k):
        if not chunks:
            return []
        model = self._ensure()
        pairs = [(query, c.text) for c in chunks]
        scores = model.predict(pairs)
        for chunk, score in zip(chunks, scores):
            chunk.score = float(score)
            chunk.scores[f"rerank:{self.model_name.split('/')[-1]}"] = float(score)
        ranked = sorted(chunks, key=lambda c: c.score, reverse=True)
        return ranked[:top_k]


class ChainReranker(BaseReranker):
    name = "chain"

    def __init__(self, rerankers: list[BaseReranker]) -> None:
        self.rerankers = rerankers

    def rerank(self, query, chunks, top_k):
        # Intermediate stages keep a wider window than the final top_k so a
        # good passage isn't dropped before the strongest model sees it.
        window = max(top_k, 10)
        for i, rr in enumerate(self.rerankers):
            last = i == len(self.rerankers) - 1
            chunks = rr.rerank(query, chunks, top_k if last else window)
        return chunks
