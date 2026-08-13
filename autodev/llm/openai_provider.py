"""OpenAI (and OpenAI-compatible) chat provider using the streaming API."""
from __future__ import annotations

import json

import httpx

from .base import LLMProvider, Message, TokenCallback


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 600):
        if not api_key:
            raise ValueError(
                "OpenAI API key is not set. Set AUTODEV_OPENAI_API_KEY or switch "
                "AUTODEV_LLM_PROVIDER=ollama."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        on_token: TokenCallback = None,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise RuntimeError(
                        f"OpenAI API error {resp.status_code}: {body[:500]}"
                    )
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        obj.get("choices", [{}])[0].get("delta", {}).get("content")
                    )
                    if delta:
                        chunks.append(delta)
                        if on_token:
                            await on_token(delta)
        return "".join(chunks)

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return r.status_code < 500
        except Exception:
            return False
