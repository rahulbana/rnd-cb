"""Travel Orchestrator (spec sections 7 & 9).

Responsibilities:
  * turn an intent into a set of agents to run,
  * schedule them in dependency layers with parallel execution inside a layer,
  * merge validated results into TripState,
  * synthesise highlights / detect conflicts,
  * stream safe progress events (no chain-of-thought — spec section 25).
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from ..agents import ALL_AGENTS, AgentContext, get_agent
from ..config.logging import get_logger
from ..llm import AgentRuntime
from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.chat import StreamEvent
from ..schemas.common import DataPoint, DataTrust
from ..schemas.trip import TripState, TripStatus
from ..tools import ToolRegistry, build_default_registry
from .intent import INTENT_TO_AGENT, Intent, IntentResult, detect_intent
from .merge import merge_result

logger = get_logger(__name__)

EventSink = Callable[[StreamEvent], Awaitable[None]]

# Agents that make up a full trip plan (spec section 8's roster).
FULL_PLAN_AGENTS = list(ALL_AGENTS.keys())


async def _null_sink(_: StreamEvent) -> None:
    return None


class Orchestrator:
    def __init__(self, runtime: AgentRuntime | None = None, tools: ToolRegistry | None = None) -> None:
        self.runtime = runtime or AgentRuntime()
        self.tools = tools or build_default_registry()

    # -- Public API ---------------------------------------------------------
    async def plan_trip(self, trip: TripState, sink: EventSink | None = None) -> list[AgentResult]:
        trip.status = TripStatus.PLANNING
        results = await self.run_agents(trip, FULL_PLAN_AGENTS, sink)
        self._synthesize(trip, results)
        trip.status = TripStatus.PLANNED if any(
            r.status in (AgentStatus.OK, AgentStatus.PARTIAL) for r in results
        ) else TripStatus.FAILED
        return results

    async def run_intent(self, trip: TripState, text: str, sink: EventSink | None = None) -> tuple[IntentResult, list[AgentResult]]:
        intent = detect_intent(text)
        if intent.intent in (Intent.PLAN_TRIP,):
            return intent, await self.plan_trip(trip, sink)
        if intent.intent is Intent.OPTIMIZE:
            # Re-run the cost-sensitive agents.
            return intent, await self.run_agents(trip, ["activity", "budget", "itinerary"], sink)
        agent = INTENT_TO_AGENT.get(intent.intent)
        if agent:
            return intent, await self.run_agents(trip, [agent], sink)
        return intent, []

    async def run_agents(self, trip: TripState, agent_names: list[str], sink: EventSink | None = None) -> list[AgentResult]:
        sink = sink or _null_sink
        layers = self._layer(agent_names)
        collected: list[AgentResult] = []
        for layer in layers:
            await sink(StreamEvent(type="status", message=f"Running: {', '.join(layer)}"))
            ctx_emit = self._make_emit(sink)
            coros = [
                get_agent(name).run(AgentContext(trip=trip, runtime=self.runtime,
                                                 tools=self.tools, emit=ctx_emit))
                for name in layer
            ]
            results = await asyncio.gather(*coros)
            # Merge sequentially (deterministic) after the parallel wave.
            for result in results:
                merge_result(trip, result)
                collected.append(result)
                await sink(StreamEvent(type="agent_done", agent=result.agent,
                                       message=result.summary,
                                       data={"status": result.status.value}))
        return collected

    # -- Internals ----------------------------------------------------------
    def _make_emit(self, sink: EventSink):
        async def emit(event: str, message: str) -> None:
            await sink(StreamEvent(type=event, agent=message if event.startswith("agent") else None,
                                   message="" if event.startswith("agent") else message))
        return emit

    @staticmethod
    def _layer(agent_names: list[str]) -> list[list[str]]:
        """Kahn-style topological layering over agent ``depends_on`` (spec section 9)."""
        wanted = set(agent_names)
        deps: dict[str, set[str]] = {}
        for name in wanted:
            agent = ALL_AGENTS[name]
            deps[name] = {d for d in agent.depends_on if d in wanted}

        layers: list[list[str]] = []
        remaining = dict(deps)
        while remaining:
            ready = sorted(n for n, d in remaining.items() if not d)
            if not ready:  # cycle guard — run the rest together
                ready = sorted(remaining)
            layers.append(ready)
            for n in ready:
                remaining.pop(n, None)
            for d in remaining.values():
                d.difference_update(ready)
        return layers

    def _synthesize(self, trip: TripState, results: list[AgentResult]) -> None:
        """Aggregate highlights and detect conflicts (spec section 9)."""
        highlights: list[DataPoint[str]] = []
        if trip.destination_overview:
            highlights.append(DataPoint(
                value=trip.destination_overview.get("summary", "")[:220],
                source="destination-agent", trust=DataTrust.AI_RECOMMENDATION, confidence=0.5,
            ))
        if trip.budget and trip.budget.total_comfort:
            b = trip.budget
            highlights.append(DataPoint(
                value=f"Estimated comfort budget: {b.total_comfort.amount:,.0f} {b.currency}",
                source="budget-engine", trust=DataTrust.ESTIMATED, confidence=0.45,
            ))
            if b.within_budget is False:
                trip.warnings.append("Estimated cost exceeds your stated budget — see budget advice.")
        if trip.weather:
            w = trip.weather
            highlights.append(DataPoint(
                value=f"{w.get('season','').title()} weather ~{w.get('typical_low_c')}–{w.get('typical_high_c')}°C",
                source="weather-agent", trust=DataTrust.ESTIMATED, confidence=0.4,
            ))
        trip.highlights = highlights

        # Feasibility: itinerary vs duration.
        if trip.itinerary and trip.request.duration_days:
            if len(trip.itinerary) != trip.request.duration_days:
                trip.warnings.append(
                    f"Itinerary covers {len(trip.itinerary)} day(s) vs requested "
                    f"{trip.request.duration_days}."
                )
        # De-duplicate warnings, keep order.
        seen: set[str] = set()
        trip.warnings = [w for w in trip.warnings if not (w in seen or seen.add(w))]
