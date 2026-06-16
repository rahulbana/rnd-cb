"""Shared infrastructure for the LLM-backed agents.

Every agent in the pipeline talks to the same OpenAI chat model. This module
centralises that interaction so the individual agents only have to worry about
their prompts, and so error handling / JSON parsing is implemented exactly
once.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from openai import OpenAI, OpenAIError

from app.config import get_settings

logger = logging.getLogger(__name__)


class AgentError(RuntimeError):
    """Raised when an agent cannot produce a usable result.

    The orchestrator and API layer convert this into a clean HTTP error so the
    frontend never sees a raw stack trace.
    """


class BaseAgent:
    """Base class providing a guarded OpenAI chat-completion call.

    Subclasses implement their own public method (e.g. ``plan``, ``write``,
    ``review``) and delegate the network call to :meth:`_complete`.

    Args:
        name: Human readable agent name, used in logs and error messages.
        client: Optional pre-built OpenAI client. Injecting a client keeps the
            class testable; when omitted a client is created from settings.
    """

    def __init__(self, name: str, client: Optional[OpenAI] = None) -> None:
        self.name = name
        settings = get_settings()
        self._model = settings.openai_model
        self._temperature = settings.openai_temperature
        # The client is created lazily-ish here; constructing OpenAI() reads the
        # OPENAI_API_KEY from the environment automatically, but we pass it
        # explicitly so a misconfiguration fails fast and clearly.
        if client is not None:
            self._client = client
        else:
            if not settings.openai_api_key:
                raise AgentError(
                    "OPENAI_API_KEY is not configured. Set it in the backend "
                    "environment before generating code."
                )
            self._client = OpenAI(api_key=settings.openai_api_key)

    def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        as_json: bool = False,
    ) -> str:
        """Call the chat model and return the assistant's text content.

        Args:
            system_prompt: Instruction that frames the agent's role.
            user_prompt: The task-specific content.
            as_json: When ``True`` the model is asked to return strict JSON via
                response_format, which the caller can then parse.

        Returns:
            The assistant message content as a string.

        Raises:
            AgentError: If the OpenAI call fails or returns no content.
        """
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if as_json:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self._client.chat.completions.create(**kwargs)
        except OpenAIError as exc:  # network, auth, rate-limit, etc.
            logger.exception("%s agent: OpenAI request failed", self.name)
            raise AgentError(
                f"The {self.name} agent could not reach the language model: {exc}"
            ) from exc

        if not response.choices or not response.choices[0].message.content:
            raise AgentError(f"The {self.name} agent received an empty response.")

        return response.choices[0].message.content.strip()

    def _complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call the model expecting JSON and parse it defensively.

        Raises:
            AgentError: If the response is not valid JSON.
        """
        raw = self._complete(system_prompt, user_prompt, as_json=True)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("%s agent returned invalid JSON: %s", self.name, raw[:500])
            raise AgentError(
                f"The {self.name} agent returned a malformed response."
            ) from exc
        if not isinstance(parsed, dict):
            raise AgentError(
                f"The {self.name} agent returned an unexpected response shape."
            )
        return parsed
