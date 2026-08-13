"""LLM provider abstraction with pluggable backends (OpenAI / Ollama)."""

from .base import LLMProvider, LLMError
from .factory import build_provider

__all__ = ["LLMProvider", "LLMError", "build_provider"]
