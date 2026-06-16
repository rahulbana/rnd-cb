"""The interface every LLM provider implements.

Agents talk to an :class:`LLMProvider` instead of a vendor SDK. A provider
must be able to return both free text and a response parsed into a Pydantic
schema (structured output). How it achieves the latter — native structured
outputs, JSON mode, tool calls, or post-hoc parsing — is up to the provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Type, TypedDict, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Message(TypedDict):
    """A single chat message in the vendor-neutral format."""

    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(ABC):
    """Vendor-neutral chat LLM used by the agents."""

    #: Friendly identifier, e.g. "openai".
    name: str = "llm"

    #: The model id this provider is configured to use (for logging).
    model: str = ""

    @abstractmethod
    def complete(self, messages: List[Message], temperature: float = 0.7) -> str:
        """Return a plain-text completion for ``messages``."""

    @abstractmethod
    def complete_structured(
        self,
        messages: List[Message],
        schema: Type[T],
        temperature: float = 0.7,
    ) -> T:
        """Return a completion parsed into the Pydantic ``schema``."""
