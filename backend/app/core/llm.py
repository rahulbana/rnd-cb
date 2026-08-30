"""OpenAI client factory and a resilient chat helper.

Responsibilities:
- Build a single, reused OpenAI client (connection pooling).
- Wrap chat completions with bounded retries, timeouts, and JSON-mode support.
- Never leak API keys into logs.

The rest of the codebase depends on the thin `LLMClient` abstraction, not on the
OpenAI SDK directly, so the provider can be swapped without touching agents.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Errors that are worth retrying (transient / server-side).
_RETRYABLE = (APIConnectionError, RateLimitError)


class LLMError(RuntimeError):
    """Raised when the LLM call fails in a non-recoverable way."""


class LLMNotConfigured(LLMError):
    """Raised when an LLM call is attempted without an API key."""


class LLMClient:
    """Thin, testable wrapper around the OpenAI chat completions API."""

    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._settings.llm_enabled

    def _ensure_client(self) -> OpenAI:
        if not self._settings.llm_enabled:
            raise LLMNotConfigured("OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = OpenAI(
                api_key=self._settings.openai_api_key,
                timeout=self._settings.openai_timeout_seconds,
                # We handle retries ourselves for consistent observability.
                max_retries=0,
            )
        return self._client

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Run a chat completion in JSON mode and return the parsed object.

        Raises:
            LLMNotConfigured: if no API key is set.
            LLMError: on transport failure or unparseable output.
        """
        client = self._ensure_client()

        @retry(
            retry=retry_if_exception_type(_RETRYABLE),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(max(1, self._settings.openai_max_retries)),
            reraise=True,
        )
        def _call() -> str:
            response = client.chat.completions.create(
                model=self._settings.openai_model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            logger.info(
                "llm_completion",
                extra={
                    "extra": {
                        "model": self._settings.openai_model,
                        "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                        "completion_tokens": getattr(
                            response.usage, "completion_tokens", None
                        ),
                    }
                },
            )
            return content

        try:
            raw = _call()
        except _RETRYABLE as exc:
            raise LLMError(f"LLM transport failure: {exc}") from exc
        except APIStatusError as exc:
            # 4xx (e.g. bad request) are not retried; surface clearly.
            raise LLMError(f"LLM API error {exc.status_code}: {exc.message}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}") from exc


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Return a process-wide cached LLM client."""
    return LLMClient(get_settings())
