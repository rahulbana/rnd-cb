"""Ollama local chat provider using the streaming /api/chat endpoint."""
from __future__ import annotations

import json

import httpx

from .base import LLMProvider, Message, TokenCallback


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        on_token: TokenCallback = None,
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise RuntimeError(
                        f"Ollama API error {resp.status_code}: {body[:500]}"
                    )
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = obj.get("message", {}).get("content")
                    if delta:
                        chunks.append(delta)
                        if on_token:
                            await on_token(delta)
                    if obj.get("done"):
                        break
        return "".join(chunks)

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code < 500
        except Exception:
            return False
