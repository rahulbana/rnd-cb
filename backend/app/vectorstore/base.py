"""Vector store interface.

A record is a chunk plus its embedding and metadata. The store owns
persistence and nearest-neighbour search; retrieval strategies compose on top.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float  # higher = more similar


class BaseVectorStore(ABC):
    @abstractmethod
    def add(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    def query(self, embedding: list[float], top_k: int,
              where: dict | None = None) -> list[SearchResult]: ...

    @abstractmethod
    def all_documents(self) -> list[SearchResult]:
        """Return every stored chunk (used to build the keyword index)."""

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def list_sources(self) -> list[dict]:
        """Distinct ingested source documents with chunk counts."""

    @abstractmethod
    def delete_source(self, source: str) -> None: ...
