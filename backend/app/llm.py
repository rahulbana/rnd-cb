"""OpenAI client wrapper with streaming support.

Handles model configuration, temperature-support gating, and translates SDK
errors into a small set of exceptions the API layer can present cleanly.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import openai
from openai import AsyncOpenAI

from .config import Settings, get_settings
from .logging_config import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when the LLM request fails in a way we want to surface."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Model families that reject a custom `temperature` value (they only accept the
# default of 1 and return HTTP 400 otherwise). OpenAI's reasoning models
# (o1 / o3 / o4 / gpt-5 generations) removed sampling controls.
_NO_SAMPLING_PREFIXES = (
    "o1",
    "o3",
    "o4",
    "gpt-5",
)


def model_supports_temperature(model: str) -> bool:
    """Return True if the model accepts a custom `temperature` parameter.

    Standard chat models (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, ...)
    accept sampling parameters; reasoning models do not.
    """
    return not any(model.startswith(prefix) for prefix in _NO_SAMPLING_PREFIXES)


class LLMClient:
    """Thin async wrapper around the OpenAI SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

    @property
    def model(self) -> str:
        return self.settings.model

    def _get_client(self) -> AsyncOpenAI:
        """Lazily construct the AsyncOpenAI client.

        Construction is deferred (and happens inside the streaming try-block)
        so that a missing API key surfaces as a graceful error rather than a
        crash at request-handling time. AsyncOpenAI resolves credentials from
        OPENAI_API_KEY when no explicit key is provided.
        """
        if self._client is None:
            kwargs: dict = {}
            if self.settings.openai_api_key:
                kwargs["api_key"] = self.settings.openai_api_key
            if self.settings.openai_base_url:
                kwargs["base_url"] = self.settings.openai_base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

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
        # OpenAI takes the system prompt as the first message in the list.
        payload: list[dict[str, str]] = []
        if system_prompt:
            payload.append({"role": "system", "content": system_prompt})
        payload.extend(messages)

        request_kwargs: dict = {
            "model": self.model,
            "messages": payload,
            "max_completion_tokens": self.settings.max_tokens,
            "stream": True,
        }

        # Only send temperature to models that accept a custom value, otherwise
        # the API returns a 400. For unsupported models the stored temperature
        # is kept for the UI but simply not applied.
        if model_supports_temperature(self.model):
            request_kwargs["temperature"] = temperature
        else:
            logger.debug(
                "Model %s does not support temperature; ignoring value %.2f",
                self.model,
                temperature,
            )

        try:
            client = self._get_client()
            stream = await client.chat.completions.create(**request_kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except openai.AuthenticationError as exc:
            logger.error("OpenAI authentication failed: %s", exc)
            raise LLMError(
                "LLM authentication failed. Check OPENAI_API_KEY.",
                status_code=502,
            ) from exc
        except openai.RateLimitError as exc:
            logger.warning("OpenAI rate limit hit: %s", exc)
            raise LLMError(
                "The assistant is rate limited. Please try again shortly.",
                status_code=429,
            ) from exc
        except openai.BadRequestError as exc:
            logger.error("OpenAI bad request: %s", exc)
            raise LLMError(f"Invalid request to LLM: {exc}", status_code=400) from exc
        except openai.APIConnectionError as exc:
            logger.error("OpenAI connection error: %s", exc)
            raise LLMError(
                "Could not reach the LLM service. Please try again.",
                status_code=503,
            ) from exc
        except openai.APIStatusError as exc:
            logger.error("OpenAI API error %s: %s", exc.status_code, exc)
            raise LLMError(
                f"LLM service error ({exc.status_code}).", status_code=502
            ) from exc
        except openai.OpenAIError as exc:
            # Catch-all for SDK errors, including a missing API key raised at
            # request time when no credentials can be resolved.
            message = str(exc)
            if "api_key" in message.lower() or "api key" in message.lower():
                logger.error("No OpenAI credentials configured: %s", exc)
                raise LLMError(
                    "The assistant is not configured. Set OPENAI_API_KEY "
                    "on the server.",
                    status_code=503,
                ) from exc
            logger.error("OpenAI error: %s", exc)
            raise LLMError("LLM service error.", status_code=502) from exc


_client_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a process-wide LLMClient singleton."""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = LLMClient()
    return _client_singleton
