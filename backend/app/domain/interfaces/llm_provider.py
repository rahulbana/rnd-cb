"""LLMProvider port -- any chat/completion backend must satisfy this."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import ChatMessage, LLMResponse

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class LLMProvider(Protocol):
    """Any chat/completion backend must satisfy this."""

    name: str  # "openai" | "anthropic" | "gemini" | "ollama"

    @classmethod
    def from_settings(cls, settings: Settings) -> LLMProvider:
        """Construct the adapter from application settings."""
        ...

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        """Return a single completed response."""
        ...

    def stream(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        """Yield response tokens as they are produced.

        Declared as a regular ``def`` returning an ``AsyncIterator`` so async
        generator implementations (``async def`` + ``yield``) match this port.
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Return the provider's token count for ``text``."""
        ...
