"""Provider-agnostic LLM interface.

Both providers speak the same small contract: given a list of chat messages,
stream back text tokens and return the full concatenated response. We call the
HTTP APIs directly with httpx so streaming behaves identically for OpenAI and
Ollama without pulling in two heavyweight SDKs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

# A callback invoked with each incremental token/delta of text.
TokenCallback = Optional[Callable[[str], Awaitable[None]]]

Message = dict  # {"role": "system"|"user"|"assistant", "content": str}


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        on_token: TokenCallback = None,
    ) -> str:
        """Run a chat completion, streaming tokens through ``on_token``.

        Returns the full response text.
        """
        raise NotImplementedError

    async def health(self) -> bool:
        """Best-effort connectivity/config check."""
        return True
