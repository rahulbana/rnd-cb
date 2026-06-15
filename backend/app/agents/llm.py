"""LLM client factory and structured-output runner.

Node modules call ``llm.run_structured(...)`` via this module (not by importing
the function directly) so it can be cleanly substituted in tests.
"""
from __future__ import annotations

from typing import Type, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, LLMError

T = TypeVar("T", bound=BaseModel)


def build_llm(temperature: float = 0.3) -> BaseChatModel:
    """Create a ChatOpenAI client from configured settings."""
    settings = get_settings()
    if not settings.has_api_key:
        raise ConfigurationError(
            "OPENAI_API_KEY is not set. Add it to backend/.env before generating a plan."
        )
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
    )


async def run_structured(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    temperature: float = 0.3,
) -> T:
    """Invoke the LLM and coerce the response into a Pydantic schema."""
    llm = build_llm(temperature=temperature).with_structured_output(schema)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    try:
        result = await llm.ainvoke(messages)
    except ConfigurationError:
        raise
    except Exception as exc:  # network, parsing, rate-limit, etc.
        raise LLMError(f"LLM call failed: {exc}") from exc
    return result  # type: ignore[return-value]
