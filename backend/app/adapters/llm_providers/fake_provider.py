"""In-memory fake LLM provider -- echoes a deterministic grounded answer."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING

from app.domain.models import ChatMessage, LLMResponse

if TYPE_CHECKING:
    from app.core.config import Settings


class FakeLLMProvider:
    """Returns a canned, deterministic response with no network call."""

    name = "fake"

    def __init__(self) -> None:
        self.model = "fake-llm-v1"

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeLLMProvider:
        return cls()

    def _answer(self, messages: Sequence[ChatMessage]) -> str:
        last = messages[-1].content if messages else ""
        return f"[fake-llm] echo: {last}"

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        content = self._answer(messages)
        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_in=sum(self.count_tokens(m.content) for m in messages),
            tokens_out=self.count_tokens(content),
        )

    async def stream(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        for token in self._answer(messages).split(" "):
            yield token + " "

    def count_tokens(self, text: str) -> int:
        return len(text.split())
