"""Anthropic Claude client wrapper with streaming support.

Handles model configuration, temperature-support gating, and translates SDK
errors into a small set of exceptions the API layer can present cleanly.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import anthropic

from .config import Settings, get_settings
from .logging_config import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when the LLM request fails in a way we want to surface."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Model families that reject the `temperature` sampling parameter (they return
# HTTP 400 if it is sent). Frontier models from the Opus 5 / Sonnet 5 / Opus 4.7+
# generation removed sampling controls in favour of `effort`.
_NO_SAMPLING_PREFIXES = (
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
)


def model_supports_temperature(model: str) -> bool:
    """Return True if the model accepts the `temperature` parameter.

    Older / smaller models (haiku-4-5, sonnet-4-6, opus-4-6, ...) still accept
    sampling parameters; the current frontier models do not.
    """
    return not any(model.startswith(prefix) for prefix in _NO_SAMPLING_PREFIXES)


class LLMClient:
    """Thin async wrapper around the Anthropic SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        # AsyncAnthropic resolves credentials from ANTHROPIC_API_KEY (or an
        # `ant auth login` profile) when no explicit key is provided.
        kwargs = {}
        if self.settings.anthropic_api_key:
            kwargs["api_key"] = self.settings.anthropic_api_key
        self._client = anthropic.AsyncAnthropic(**kwargs)

    @property
    def model(self) -> str:
        return self.settings.model

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream the assistant response as text chunks.

        Yields incremental text deltas. Raises ``LLMError`` on failure.
        """
        request_kwargs: dict = {
            "model": self.model,
            "max_tokens": self.settings.max_tokens,
            "messages": messages,
            "output_config": {"effort": self.settings.effort},
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt

        # Only send temperature to models that accept it, otherwise the API
        # returns a 400. For unsupported models the stored temperature is kept
        # for the UI but simply not applied. `temperature` is passed via
        # extra_body because the 1.x SDK no longer types it as a keyword arg.
        if model_supports_temperature(self.model):
            request_kwargs["extra_body"] = {"temperature": temperature}
        else:
            logger.debug(
                "Model %s does not support temperature; ignoring value %.2f",
                self.model,
                temperature,
            )

        try:
            async with self._client.messages.stream(**request_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError as exc:
            logger.error("Anthropic authentication failed: %s", exc)
            raise LLMError(
                "LLM authentication failed. Check ANTHROPIC_API_KEY.",
                status_code=502,
            ) from exc
        except anthropic.RateLimitError as exc:
            logger.warning("Anthropic rate limit hit: %s", exc)
            raise LLMError(
                "The assistant is rate limited. Please try again shortly.",
                status_code=429,
            ) from exc
        except anthropic.BadRequestError as exc:
            logger.error("Anthropic bad request: %s", exc)
            raise LLMError(f"Invalid request to LLM: {exc}", status_code=400) from exc
        except anthropic.APIConnectionError as exc:
            logger.error("Anthropic connection error: %s", exc)
            raise LLMError(
                "Could not reach the LLM service. Please try again.",
                status_code=503,
            ) from exc
        except anthropic.APIStatusError as exc:
            logger.error("Anthropic API error %s: %s", exc.status_code, exc)
            raise LLMError(
                f"LLM service error ({exc.status_code}).", status_code=502
            ) from exc
        except TypeError as exc:
            # The SDK raises TypeError when no credentials can be resolved
            # (no ANTHROPIC_API_KEY and no `ant auth login` profile).
            if "authentication" in str(exc).lower():
                logger.error("No Anthropic credentials configured: %s", exc)
                raise LLMError(
                    "The assistant is not configured. Set ANTHROPIC_API_KEY "
                    "on the server.",
                    status_code=503,
                ) from exc
            raise


_client_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a process-wide LLMClient singleton."""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = LLMClient()
    return _client_singleton
