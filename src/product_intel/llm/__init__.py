"""Provider-agnostic LLM layer.

The agents depend only on the :class:`~product_intel.llm.base.LLMClient`
interface. Two implementations ship:

* :class:`~product_intel.llm.offline.OfflineLLM` - deterministic, template-based,
  no network or API key required (the default, so the pipeline always runs).
* :class:`~product_intel.llm.anthropic_client.AnthropicLLM` - calls the Claude
  API for richer synthesis (opt-in, imported lazily).
"""

from __future__ import annotations

from .base import LLMClient
from .offline import OfflineLLM


def get_llm(provider: str = "offline", **kwargs) -> LLMClient:
    """Factory returning an :class:`LLMClient` for ``provider``.

    ``provider`` is one of ``"offline"`` (default), ``"anthropic"`` or
    ``"openai"``. The hosted clients are imported lazily so their dependencies
    stay optional.
    """

    provider = (provider or "offline").lower()
    if provider == "offline":
        return OfflineLLM()
    if provider == "anthropic":
        from .anthropic_client import AnthropicLLM

        return AnthropicLLM(**kwargs)
    if provider == "openai":
        from .openai_client import OpenAILLM

        return OpenAILLM(**kwargs)
    raise ValueError(
        f"Unknown LLM provider: {provider!r} (expected 'offline', 'anthropic' or 'openai')"
    )


__all__ = ["LLMClient", "OfflineLLM", "get_llm"]
