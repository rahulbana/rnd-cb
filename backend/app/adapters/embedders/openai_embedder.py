"""OpenAI embedder adapter -- lazy client, provider-neutral output."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import EmbeddingVector

if TYPE_CHECKING:
    from app.core.config import Settings


class OpenAIEmbedder:
    """Embeds text via the OpenAI embeddings API."""

    name = "openai"

    def __init__(self, model: str, dim: int, api_key: str | None) -> None:
        self.model = model
        self.dim = dim
        self._api_key = api_key
        self._client: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAIEmbedder:
        return cls(
            model=settings.OPENAI_EMBED_MODEL,
            dim=settings.OPENAI_EMBED_DIM,
            api_key=settings.OPENAI_API_KEY,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI  # lazy import

            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def embed_documents(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        if not texts:
            return []
        client = self._get_client()
        resp = await client.embeddings.create(model=self.model, input=list(texts))
        return [
            EmbeddingVector.of(item.embedding, model=self.model) for item in resp.data
        ]

    async def embed_query(self, text: str) -> EmbeddingVector:
        vectors = await self.embed_documents([text])
        return vectors[0]
