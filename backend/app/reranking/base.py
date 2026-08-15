"""Reranker interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..retrieval.base import RetrievedChunk


class BaseReranker(ABC):
    name: str = "base"

    @abstractmethod
    def rerank(self, query: str, chunks: list[RetrievedChunk],
               top_k: int) -> list[RetrievedChunk]: ...
