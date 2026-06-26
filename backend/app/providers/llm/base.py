"""Abstract base for pluggable LLM providers."""
from __future__ import annotations

import abc
from typing import Optional

from langchain_core.language_models import BaseChatModel


class BaseLLMProvider(abc.ABC):
    """Wraps a chat-model backend behind a stable interface.

    Returning a LangChain ``BaseChatModel`` lets the agent nodes use a uniform
    ``ainvoke`` / ``astream`` API regardless of the underlying vendor.
    """

    name: str = "base"

    @abc.abstractmethod
    def chat_model(
        self, *, streaming: bool = False, max_tokens: Optional[int] = None
    ) -> BaseChatModel:
        """Return a configured chat model instance."""
        raise NotImplementedError
