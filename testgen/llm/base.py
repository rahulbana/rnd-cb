"""Base contract shared by every LLM backend."""

from __future__ import annotations

import abc
from dataclasses import dataclass


class LLMError(RuntimeError):
    """Raised when a provider cannot be reached or returns an error."""


@dataclass
class LLMProvider(abc.ABC):
    """Abstract chat-completion provider.

    Concrete providers only need to implement :meth:`complete`. Everything
    else in the agent talks to this small surface, which is what makes the
    backend swappable (OpenAI <-> Ollama <-> anything else).
    """

    model: str
    temperature: float = 0.2
    timeout: float = 120.0

    @abc.abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the assistant's reply for the given system/user prompts."""

    @property
    def name(self) -> str:
        return type(self).__name__.replace("Provider", "").lower()
