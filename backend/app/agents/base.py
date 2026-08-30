"""Base agent abstraction (spec section 7 — specialised agents, not one god-agent).

Each agent is small and single-purpose. It reads the shared ``TripState`` from
the :class:`AgentContext`, may call tools, produces validated structured data,
and returns an :class:`AgentResult`. Agents never mutate ``TripState`` directly;
the orchestrator merges results, keeping execution testable and side-effect free.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..config.logging import get_logger
from ..llm import AgentRuntime, TaskComplexity
from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.trip import TripState
from ..tools import ToolRegistry

logger = get_logger(__name__)

EmitFn = Callable[[str, str], Awaitable[None]]


async def _noop_emit(event: str, message: str) -> None:  # pragma: no cover
    return None


@dataclass
class AgentContext:
    trip: TripState
    runtime: AgentRuntime
    tools: ToolRegistry
    emit: EmitFn = _noop_emit
    scratch: dict = field(default_factory=dict)


class BaseAgent(abc.ABC):
    name: str = "agent"
    description: str = ""
    complexity: TaskComplexity = TaskComplexity.MODERATE
    # Sections of TripState this agent depends on being populated first.
    depends_on: tuple[str, ...] = ()

    @abc.abstractmethod
    async def _run(self, ctx: AgentContext) -> AgentResult:
        ...

    async def run(self, ctx: AgentContext) -> AgentResult:
        started = time.perf_counter()
        await ctx.emit("agent_started", self.name)
        try:
            result = await self._run(ctx)
        except Exception as exc:  # an agent failure must never crash the run
            logger.exception("agent %s failed", self.name)
            result = AgentResult(
                agent=self.name, status=AgentStatus.FAILED, error=str(exc),
                summary=f"{self.name} could not complete.",
            )
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        await ctx.emit("agent_done", self.name)
        return result

    # Convenience for subclasses -------------------------------------------
    def _result(self, **kwargs) -> AgentResult:
        kwargs.setdefault("agent", self.name)
        return AgentResult(**kwargs)
