"""LLM provider interface — async token streaming."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

# A chat message: {"role": "system"|"user"|"assistant", "content": str}
Message = dict[str, str]


class BaseLLM(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """Yield output token-by-token (or in small chunks)."""
        raise NotImplementedError
        yield  # pragma: no cover  (makes this an async generator)

    async def complete(self, messages: list[Message]) -> str:
        return "".join([tok async for tok in self.stream(messages)])
