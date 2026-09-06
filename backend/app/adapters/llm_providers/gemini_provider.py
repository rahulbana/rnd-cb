"""Google Gemini chat adapter -- lazy client, provider-neutral shapes."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import ChatMessage, LLMResponse, Role

if TYPE_CHECKING:
    from app.core.config import Settings

# Internal role -> Gemini role.
_ROLE = {Role.USER: "user", Role.ASSISTANT: "model"}


class GeminiProvider:
    """Chat over Google's Generative AI (Gemini) API."""

    name = "gemini"

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self.model = model
        self._configured = False

    @classmethod
    def from_settings(cls, settings: Settings) -> GeminiProvider:
        return cls(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)

    def _model(self, system: str) -> Any:
        import google.generativeai as genai  # lazy import

        if not self._configured:
            genai.configure(api_key=self._api_key)
            self._configured = True
        return genai.GenerativeModel(self.model, system_instruction=system or None)

    @staticmethod
    def _split(messages: Sequence[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        system = "\n\n".join(m.content for m in messages if m.role == Role.SYSTEM)
        contents = [
            {"role": _ROLE.get(m.role, "user"), "parts": [m.content]}
            for m in messages
            if m.role != Role.SYSTEM
        ]
        return system, contents

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        system, contents = self._split(messages)
        model = self._model(system)
        started = time.perf_counter()
        resp = await model.generate_content_async(
            contents, generation_config={"temperature": temperature}
        )
        latency_ms = (time.perf_counter() - started) * 1000
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            content=resp.text,
            provider=self.name,
            model=self.model,
            tokens_in=getattr(usage, "prompt_token_count", 0) or 0,
            tokens_out=getattr(usage, "candidates_token_count", 0) or 0,
            latency_ms=latency_ms,
        )

    async def stream(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        system, contents = self._split(messages)
        model = self._model(system)
        stream = await model.generate_content_async(
            contents,
            generation_config={"temperature": temperature},
            stream=True,
        )
        async for chunk in stream:
            if getattr(chunk, "text", None):
                yield chunk.text

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
