"""Anthropic (Claude) chat adapter -- lazy client, provider-neutral shapes."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import ChatMessage, LLMResponse, Role

if TYPE_CHECKING:
    from app.core.config import Settings


class AnthropicProvider:
    """Chat over the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: str | None, model: str, max_tokens: int) -> None:
        self._api_key = api_key
        self.model = model
        self._max_tokens = max_tokens
        self._client: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> AnthropicProvider:
        return cls(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic  # lazy import

            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    @staticmethod
    def _split(messages: Sequence[ChatMessage]) -> tuple[str, list[dict[str, str]]]:
        # Anthropic takes the system prompt separately from the turn list.
        system = "\n\n".join(m.content for m in messages if m.role == Role.SYSTEM)
        turns = [
            {"role": m.role.value, "content": m.content}
            for m in messages
            if m.role != Role.SYSTEM
        ]
        return system, turns

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        system, turns = self._split(messages)
        started = time.perf_counter()
        resp = await self._get_client().messages.create(
            model=self.model,
            system=system,
            messages=turns,
            max_tokens=self._max_tokens,
            temperature=temperature,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(
            content=text,
            provider=self.name,
            model=self.model,
            tokens_in=getattr(resp.usage, "input_tokens", 0) or 0,
            tokens_out=getattr(resp.usage, "output_tokens", 0) or 0,
            latency_ms=latency_ms,
        )

    async def stream(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        system, turns = self._split(messages)
        async with self._get_client().messages.stream(
            model=self.model,
            system=system,
            messages=turns,
            max_tokens=self._max_tokens,
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
