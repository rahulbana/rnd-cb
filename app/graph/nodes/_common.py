"""Shared helpers for nodes: budgeted structured LLM calls."""

from __future__ import annotations

from typing import TypeVar

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.budget import BudgetTracker
from app.graph.context import RuntimeContext

T = TypeVar("T", bound=BaseModel)


async def structured_call(
    ctx: RuntimeContext,
    budget: BudgetTracker,
    *,
    schema: type[T],
    system: str,
    human: str,
    role: str = "smart",
) -> T:
    """Invoke the LLM for a validated `schema`, recording token usage into `budget`."""
    runnable = ctx.llm.structured(schema, role=role)
    result = await runnable.ainvoke(
        [("system", system), ("human", human)],
        config={"callbacks": ctx.callbacks()},
    )
    # include_raw=True → {"raw": AIMessage, "parsed": schema, "parsing_error": ...}
    raw = result.get("raw") if isinstance(result, dict) else None
    parsed = result.get("parsed") if isinstance(result, dict) else result
    if isinstance(raw, AIMessage):
        model_id = ctx.llm._model_id(role)  # noqa: SLF001 — internal helper, same package intent
        usage = ctx.llm.usage_from(raw, model_id)
        budget.record_llm(usage.model, usage.input_tokens, usage.output_tokens)
    if parsed is None:
        raise ValueError(f"structured call returned no parsed {schema.__name__}")
    return parsed  # type: ignore[return-value]
