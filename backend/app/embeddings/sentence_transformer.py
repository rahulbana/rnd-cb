"""SentenceTransformers embedding backend.

The model is loaded lazily on first use so the API can boot quickly and so
that importing this module never triggers a large download.
"""
from __future__ import annotations

from .base import BaseEmbedder
from ..config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)


class SentenceTransformerEmbedder(BaseEmbedder):
    name = "sentence_transformer"

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            log.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self.dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        batch = get_settings().embedding_batch_size
        vectors = model.encode(
            texts, batch_size=batch, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False,
        )
        return vectors.tolist()
