"""Sentence-Transformers embedder -- local, free, default in production.

The model (torch stack) loads lazily on first use so the app boots and
unrelated tests run without it installed. ``dim`` is known from config up
front so the registry can detect embedding-dimension drift on provider swaps.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import EmbeddingVector

if TYPE_CHECKING:
    from app.core.config import Settings


class SentenceTransformersEmbedder:
    """Embeds text with a local Sentence-Transformers model."""

    name = "sentence_transformers"

    def __init__(self, model: str, dim: int) -> None:
        self.model = model
        self.dim = dim
        self._st_model: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> SentenceTransformersEmbedder:
        return cls(model=settings.EMBED_MODEL, dim=settings.EMBED_DIM)

    def _model(self) -> Any:
        if self._st_model is None:
            from sentence_transformers import SentenceTransformer  # lazy import

            self._st_model = SentenceTransformer(self.model)
        return self._st_model

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._model()
        vectors = model.encode(
            list(texts), normalize_embeddings=True, convert_to_numpy=True
        )
        return [v.tolist() for v in vectors]

    async def embed_documents(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        if not texts:
            return []
        return [
            EmbeddingVector.of(values, model=self.model) for values in self._encode(texts)
        ]

    async def embed_query(self, text: str) -> EmbeddingVector:
        values = self._encode([text])[0]
        return EmbeddingVector.of(values, model=self.model)
