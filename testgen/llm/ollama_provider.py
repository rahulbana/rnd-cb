"""Ollama local-model backend (native /api/chat endpoint)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .base import LLMError, LLMProvider


@dataclass
class OllamaProvider(LLMProvider):
    """Talks to a local Ollama server.

    Uses Ollama's native REST API so it works without the OpenAI SDK or any
    API key. Point ``host`` at a remote Ollama instance if needed.
    """

    host: str | None = None

    def __post_init__(self) -> None:
        self.host = (
            self.host
            or os.environ.get("OLLAMA_HOST")
            or "http://localhost:11434"
        ).rstrip("/")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise LLMError(
                "The 'requests' package is required for the Ollama provider. "
                "Install it with: pip install requests"
            ) from exc

        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Could not reach Ollama at {self.host}. Is it running? "
                "Start it with `ollama serve` and pull a model, e.g. "
                "`ollama pull llama3`."
            ) from exc
        except Exception as exc:  # pragma: no cover - network/runtime guard
            raise LLMError(f"Ollama request failed: {exc}") from exc

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise LLMError("Ollama returned invalid JSON.") from exc

        content = (data.get("message") or {}).get("content", "")
        if not content:
            raise LLMError("Ollama returned an empty response.")
        return content
