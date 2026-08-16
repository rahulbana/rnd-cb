"""LLM provider interface — async token streaming and tool-calling."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

# A chat message: {"role": ..., "content": ...} (plus tool_calls/tool_call_id).
Message = dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string of arguments


@dataclass
class AssistantTurn:
    """One assistant step: free-text content and/or a set of tool calls."""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


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

    async def chat(self, messages: list[Message],
                   tools: list[dict] | None = None) -> AssistantTurn:
        """One non-streaming turn that may request tool calls. Providers that
        don't support tools should raise NotImplementedError."""
        raise NotImplementedError(f"{self.name} does not support tool calling")
