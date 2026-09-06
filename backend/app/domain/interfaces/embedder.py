"""Embedder port -- any text-embedding backend must satisfy this."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import EmbeddingVector

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class Embedder(Protocol):
    """Any embedding backend must satisfy this."""

    name: str  # "sentence_transformers" | "openai" | ...
    dim: int  # embedding dimensionality (drift detection hook)

    @classmethod
    def from_settings(cls, settings: Settings) -> Embedder:
        """Construct the adapter from application settings."""
        ...

    async def embed_documents(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        """Embed a batch of documents/chunks."""
        ...

    async def embed_query(self, text: str) -> EmbeddingVector:
        """Embed a single query string."""
        ...
