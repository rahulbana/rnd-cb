"""OpenAI chat adapter -- lazy client, provider-neutral request/response."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import ChatMessage, LLMResponse

if TYPE_CHECKING:
    from app.core.config import Settings


class OpenAIProvider:
    """Chat/completions over the OpenAI API."""

    name = "openai"

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self.model = model
        self._client: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAIProvider:
        return cls(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_CHAT_MODEL)

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI  # lazy import

            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @staticmethod
    def _payload(messages: Sequence[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        started = time.perf_counter()
        resp = await self._get_client().chat.completions.create(
            model=self.model,
            messages=self._payload(messages),
            temperature=temperature,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        usage = resp.usage
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            provider=self.name,
            model=self.model,
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )

    async def stream(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        stream = await self._get_client().chat.completions.create(
            model=self.model,
            messages=self._payload(messages),
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken  # lazy import

            enc = tiktoken.encoding_for_model(self.model)
            return len(enc.encode(text))
        except Exception:  # noqa: BLE001 - fall back to a rough estimate
            return max(1, len(text) // 4)
