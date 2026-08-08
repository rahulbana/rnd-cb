"""Thin wrapper around the OpenAI Chat Completions API.

Isolating the SDK here keeps the agent loop provider-agnostic and gives one
place to add retries, logging, or a different backend later.
"""

from __future__ import annotations

from openai import OpenAI


class LLMClient:
    def __init__(self, config) -> None:
        if not config.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your environment or .env file."
            )
        kwargs = {"api_key": config.openai_api_key}
        if config.openai_base_url:
            kwargs["base_url"] = config.openai_base_url
        self._client = OpenAI(**kwargs)
        self._model = config.openai_model

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """One turn of the conversation. Returns the raw API message object."""
        request = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        response = self._client.chat.completions.create(**request)
        return response.choices[0].message
