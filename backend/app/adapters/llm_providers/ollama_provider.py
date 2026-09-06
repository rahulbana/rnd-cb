"""Ollama chat adapter -- local models over HTTP (the dev default LLM).

Talks to an Ollama server via its ``/api/chat`` endpoint using httpx, so no
provider SDK is required. Streaming reads Ollama's newline-delimited JSON.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING

from app.domain.models import ChatMessage, LLMResponse

if TYPE_CHECKING:
    from app.core.config import Settings


class OllamaProvider:
    """Chat over a local Ollama server."""

    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaProvider:
        return cls(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)

    @staticmethod
    def _payload(messages: Sequence[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        import httpx  # lazy import

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": self._payload(messages),
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            provider=self.name,
            model=self.model,
            tokens_in=data.get("prompt_eval_count", 0) or 0,
            tokens_out=data.get("eval_count", 0) or 0,
            latency_ms=latency_ms,
        )

    async def stream(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        import httpx  # lazy import

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": self._payload(messages),
                    "stream": True,
                    "options": {"temperature": temperature},
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
