"""Pluggable embedding backends.

The default ``hash`` provider needs no external dependencies or model
downloads, so the app runs anywhere out of the box. For real semantic
quality switch ``EMBEDDING_PROVIDER`` to ``sentence_transformers`` (set
``EMBEDDING_MODEL=BAAI/bge-m3`` for the model from the original spec) or
``openai``.
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings


class BaseEmbedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class HashEmbedder(BaseEmbedder):
    """Deterministic bag-of-words hashing embedder.

    Not semantically strong, but dependency-free and good enough for
    local development, tests and demos. Vectors are L2-normalised so
    cosine distance behaves sensibly.
    """

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.EMBEDDING_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in text.lower().split():
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # lazy import

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return vectors.tolist()


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, model_name: str) -> None:
        from app.services.observability import get_openai_client

        self._client = get_openai_client(
            api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
        )
        self._model = model_name
        self.dim = 1536  # text-embedding-3-small

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]


@lru_cache
def get_embedder() -> BaseEmbedder:
    provider = settings.EMBEDDING_PROVIDER.lower()
    try:
        if provider == "sentence_transformers":
            return SentenceTransformerEmbedder(settings.EMBEDDING_MODEL)
        if provider == "openai":
            return OpenAIEmbedder(settings.OPENAI_EMBEDDING_MODEL)
    except Exception as exc:  # pragma: no cover - graceful degradation
        import logging

        logging.getLogger(__name__).warning(
            "Embedding provider '%s' unavailable (%s); falling back to hash.",
            provider,
            exc,
        )
    return HashEmbedder()
