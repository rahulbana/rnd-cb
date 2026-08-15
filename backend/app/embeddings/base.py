"""Embedding interface. Implementations are swappable via config."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    name: str = "base"
    dimension: int = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed documents/passages."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query. Overridden when the model uses asymmetric
        query/document encoders."""
        return self.embed([text])[0]
