"""Ollama local chat provider with streaming over its HTTP API."""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from .base import AssistantTurn, BaseLLM, Message, ToolCall
from ..config import get_settings


class OllamaLLM(BaseLLM):
    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.ollama_model
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._temperature = settings.llm_temperature
        self._num_predict = settings.llm_max_tokens

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        import httpx

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._num_predict,
            },
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break

    async def chat(self, messages: list[Message], tools=None) -> AssistantTurn:
        import httpx

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        msg = data.get("message", {})
        calls = []
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            # Ollama returns arguments as a dict; normalize to a JSON string.
            args_str = args if isinstance(args, str) else json.dumps(args)
            calls.append(ToolCall(id=uuid.uuid4().hex, name=fn.get("name", ""),
                                  arguments=args_str))
        return AssistantTurn(content=msg.get("content", "") or "", tool_calls=calls)
