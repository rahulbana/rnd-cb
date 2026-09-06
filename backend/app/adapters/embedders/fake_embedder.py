"""In-memory fake embedders.

Two distinct implementations exist so Phase 1 can prove the registry swap:
flipping ``EMBEDDER_PROVIDER`` from ``fake`` to ``fake_hash`` changes the
embedding produced with zero code changes.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.models import EmbeddingVector

if TYPE_CHECKING:
    from app.core.config import Settings

_DIM = 16


def _seeded_vector(text: str, *, salt: str, dim: int = _DIM) -> list[float]:
    """Deterministic pseudo-embedding from a hash of the text."""
    digest = hashlib.sha256(f"{salt}:{text}".encode()).digest()
    raw = [digest[i % len(digest)] / 255.0 for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]


class FakeEmbedder:
    """Deterministic hash-based fake embedder (default)."""

    name = "fake"

    def __init__(self, dim: int = _DIM) -> None:
        self.dim = dim
        self.model = "fake-embed-v1"

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeEmbedder:
        return cls()

    async def embed_documents(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        return [
            EmbeddingVector.of(
                _seeded_vector(t, salt="doc", dim=self.dim), model=self.model
            )
            for t in texts
        ]

    async def embed_query(self, text: str) -> EmbeddingVector:
        return EmbeddingVector.of(
            _seeded_vector(text, salt="doc", dim=self.dim), model=self.model
        )


class FakeHashEmbedder:
    """A second, distinct fake embedder using a different salt.

    Same interface, different output -- the proof that the registry, not the
    call site, decides which implementation runs.
    """

    name = "fake_hash"

    def __init__(self, dim: int = _DIM) -> None:
        self.dim = dim
        self.model = "fake-hash-embed-v1"

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeHashEmbedder:
        return cls()

    async def embed_documents(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        return [
            EmbeddingVector.of(
                _seeded_vector(t, salt="hash", dim=self.dim), model=self.model
            )
            for t in texts
        ]

    async def embed_query(self, text: str) -> EmbeddingVector:
        return EmbeddingVector.of(
            _seeded_vector(text, salt="hash", dim=self.dim), model=self.model
        )
