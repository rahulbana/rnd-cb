"""Shared, lazily-built engine singletons (runtime, tools, orchestrator)."""
from __future__ import annotations

from functools import lru_cache

from ..llm import AgentRuntime
from ..orchestration import Orchestrator
from ..tools import build_default_registry


@lru_cache
def get_runtime() -> AgentRuntime:
    return AgentRuntime()


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator(runtime=get_runtime(), tools=build_default_registry())
