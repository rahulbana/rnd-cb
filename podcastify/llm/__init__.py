"""Pluggable LLM providers for the thinking agents.

The agents depend only on the :class:`LLMProvider` interface, so the
underlying model vendor can be swapped without touching agent code.
OpenAI is the default implementation.
"""

from .base import LLMProvider, Message
from .factory import get_llm_provider, register_provider

__all__ = ["LLMProvider", "Message", "get_llm_provider", "register_provider"]
