"""Agent runtime — the bridge between agents and the model layer.

Provides validated structured-output generation (spec section 35). When the
model is unavailable or returns invalid JSON, the caller-supplied deterministic
fallback is used so a section is never left empty and hallucinations never
enter business logic unchecked.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from ..config.logging import get_logger
from .base import LLMMessage, LLMUsage, Role
from .router import ModelRouter, TaskComplexity

logger = get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class AgentRuntime:
    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    @property
    def offline(self) -> bool:
        return self.router.offline

    async def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[TModel],
        fallback: Callable[[], TModel],
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        temperature: float = 0.3,
    ) -> tuple[TModel, LLMUsage, bool]:
        """Return ``(instance, usage, used_llm)``.

        ``used_llm`` is False when the deterministic fallback produced the value.
        """
        if self.router.offline:
            return fallback(), LLMUsage(), False

        schema_json = json.dumps(schema.model_json_schema())
        messages = [
            LLMMessage(Role.SYSTEM, system),
            LLMMessage(
                Role.USER,
                f"{user}\n\nReturn ONLY a JSON object matching this JSON schema "
                f"(no markdown, no commentary):\n{schema_json}",
            ),
        ]
        model = self.router.select_model(complexity)
        try:
            response = await self.router.provider.complete(
                messages, model=model, temperature=temperature, max_tokens=1600, json_mode=True
            )
            payload = _extract_json(response.text)
            instance = schema.model_validate(payload)
            return instance, response.usage, True
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Structured output invalid for %s; using fallback: %s",
                           schema.__name__, exc)
            return fallback(), LLMUsage(), False
        except Exception as exc:  # network/provider errors -> graceful degradation
            logger.warning("LLM call failed for %s; using fallback: %s", schema.__name__, exc)
            return fallback(), LLMUsage(), False

    async def generate_text(
        self,
        *,
        system: str,
        user: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        temperature: float = 0.5,
        fallback: str | None = None,
    ) -> tuple[str, LLMUsage]:
        if self.router.offline and fallback is not None:
            return fallback, LLMUsage()
        messages = [LLMMessage(Role.SYSTEM, system), LLMMessage(Role.USER, user)]
        model = self.router.select_model(complexity)
        try:
            response = await self.router.provider.complete(
                messages, model=model, temperature=temperature
            )
            return response.text, response.usage
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("LLM text generation failed: %s", exc)
            return (fallback or "I could not reach the AI model just now."), LLMUsage()

    async def stream_text(
        self,
        *,
        system: str,
        user: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        temperature: float = 0.5,
    ) -> AsyncIterator[str]:
        messages = [LLMMessage(Role.SYSTEM, system), LLMMessage(Role.USER, user)]
        model = self.router.select_model(complexity)
        async for token in self.router.provider.stream(
            messages, model=model, temperature=temperature
        ):
            yield token


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        # strip markdown fences if the model wrapped output
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    return json.loads(text[start : end + 1])
