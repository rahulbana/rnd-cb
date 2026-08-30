"""Deterministic mock provider.

Lets the entire multi-agent system run offline with no API key. It returns
concise, plausible text; agents that need structured data rely on their own
deterministic fallbacks (see ``BaseAgent.build_fallback``) rather than parsing
mock JSON, which keeps offline output valid by construction.
"""
from __future__ import annotations

import hashlib
from typing import AsyncIterator

from .base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.4,
        max_tokens: int = 1200,
        json_mode: bool = False,
    ) -> LLMResponse:
        last_user = next(
            (m.content for m in reversed(messages) if m.role.value == "user"), ""
        )
        digest = hashlib.sha256(last_user.encode()).hexdigest()[:8]
        if json_mode:
            text = "{}"
        else:
            text = (
                "This is an offline-mode response generated without a live model. "
                "Set OPENAI_API_KEY to enable full AI reasoning. "
                f"(request-ref {digest})"
            )
        usage = LLMUsage(prompt_tokens=len(last_user) // 4, completion_tokens=len(text) // 4)
        return LLMResponse(text=text, model=f"mock:{model}", usage=usage, provider=self.name)

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.4,
        max_tokens: int = 1200,
    ) -> AsyncIterator[str]:
        response = await self.complete(messages, model=model)
        for word in response.text.split(" "):
            yield word + " "
