"""LLM provider abstraction (spec section 4).

The application is intentionally decoupled from any single model. Everything
talks to :class:`LLMProvider`; concrete providers (OpenAI, Mock) implement it.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    role: Role
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "LLMUsage") -> "LLMUsage":
        return LLMUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    provider: str = "unknown"


class LLMProvider(abc.ABC):
    """Common interface every model backend implements."""

    name: str = "base"

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.4,
        max_tokens: int = 1200,
        json_mode: bool = False,
    ) -> LLMResponse:
        ...

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.4,
        max_tokens: int = 1200,
    ) -> AsyncIterator[str]:
        """Default streaming: fall back to a single completion chunk."""
        response = await self.complete(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        yield response.text


# Rough per-1K-token pricing (USD) used only for cost telemetry/estimates.
# These are approximate and configurable; they are never presented as billing.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.010),
    "gpt-4o-mini": (0.00015, 0.0006),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prompt_price, completion_price = MODEL_PRICING.get(model, (0.0, 0.0))
    return (prompt_tokens / 1000) * prompt_price + (completion_tokens / 1000) * completion_price
