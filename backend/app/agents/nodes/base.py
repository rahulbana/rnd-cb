"""Shared helpers for agent nodes."""
from __future__ import annotations

import functools
import time
from typing import Awaitable, Callable

from app.agents.state import PlanState
from app.core.logging import get_logger

NodeFn = Callable[[PlanState], Awaitable[PlanState]]


def timed_node(name: str) -> Callable[[NodeFn], NodeFn]:
    """Decorate an agent node to log its start, completion and duration."""

    def decorator(fn: NodeFn) -> NodeFn:
        log = get_logger(f"agents.{name}")

        @functools.wraps(fn)
        async def wrapper(state: PlanState) -> PlanState:
            start = time.perf_counter()
            log.info("agent '%s' started", name)
            result = await fn(state)
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.info("agent '%s' finished in %.0f ms", name, elapsed_ms)
            return result

        return wrapper

    return decorator
