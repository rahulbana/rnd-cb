"""Shared OpenAI client helpers for agents."""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def complete_json(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Call the chat completions API and parse a JSON object response.

    Uses response_format=json_object so the model reliably returns parseable JSON.
    """
    client = get_client()
    model = model or settings.openai_model

    resp = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from model: %s", content[:500])
        return {}
