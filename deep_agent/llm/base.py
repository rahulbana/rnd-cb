"""LLM provider abstraction.

A provider is a small, self-contained spec that knows how to build a
LangChain chat model for one back-end, which credential it needs, and which
package to install.  New providers implement :class:`LLMProviderSpec` and
register themselves — nothing else in the codebase changes.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel


@dataclass(frozen=True)
class LLMParams:
    """Resolved, provider-agnostic generation parameters."""

    model: str
    temperature: float
    max_tokens: int | None
    timeout: int
    max_retries: int
    seed: int | None


class LLMProviderSpec(ABC):
    """Contract every LLM back-end implements."""

    #: Registry key, e.g. "openai" (lower-case).
    name: str = "base"
    #: Attribute on ``Settings`` holding the API key (may be absent).
    settings_key: str = ""
    #: Environment variable name (used for messages and as a fallback).
    env_key: str = ""
    #: pip package that provides this integration.
    package: str = ""
    #: Sensible default model for the provider.
    default_model: str = ""

    def get_api_key(self, settings) -> str | None:
        """Resolve the API key from settings, falling back to the raw env."""

        key = getattr(settings, self.settings_key, None) if self.settings_key else None
        return key or (os.environ.get(self.env_key) if self.env_key else None)

    @abstractmethod
    def build(self, settings, params: LLMParams) -> BaseChatModel:
        """Construct the LangChain chat model for this provider."""
