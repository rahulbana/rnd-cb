"""Retrieval result domain model."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.models.chunk import Chunk


class RetrievedChunk(BaseModel):
    """A chunk returned by a retriever or reranker, with its score."""

    chunk: Chunk
    score: float
    source: str = ""  # e.g. "dense" | "sparse" | "hybrid" | "reranker"
