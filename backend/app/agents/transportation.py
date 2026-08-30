"""Transportation Agent (spec section 8) — getting around locally."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.common import DataPoint, DataTrust
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class _TransportMode(BaseModel):
    mode: str
    when_to_use: str
    typical_cost: str
    convenience: str = "medium"


class _Transport(BaseModel):
    destination: str
    modes: list[_TransportMode] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)


class TransportationAgent(BaseAgent):
    name = "transportation"
    description = "Local transport options: metro, taxi, rental, walking with cost/convenience."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        system = (
            f"{GUARDRAILS} You are a local transport expert. Explain the best ways to get around, "
            "with when to use each mode, indicative cost and convenience, plus practical tips."
        )
        user = f"Explain local transportation.\n{request_brief(req)}"
        result, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=_Transport,
            fallback=lambda: self._fallback(dest),
        )
        status = AgentStatus.OK if used_llm else AgentStatus.PARTIAL
        return self._result(
            status=status,
            summary=f"{len(result.modes)} transport options for {dest}.",
            data=result.model_dump(),
            citations=[DataPoint(value="Local transport guidance", source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.5 if used_llm else 0.3)],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )

    @staticmethod
    def _fallback(dest: str) -> _Transport:
        return _Transport(
            destination=dest,
            modes=[
                _TransportMode(mode="Metro/subway", when_to_use="Cross-city, peak hours",
                               typical_cost="low", convenience="high"),
                _TransportMode(mode="Walking", when_to_use="Dense central areas",
                               typical_cost="free", convenience="high"),
                _TransportMode(mode="Taxi / ride-hail", when_to_use="Late nights, luggage",
                               typical_cost="medium", convenience="high"),
                _TransportMode(mode="Bus", when_to_use="Areas without metro",
                               typical_cost="low", convenience="medium"),
            ],
            tips=["Get a stored-value transit card", "Avoid rush hour with luggage",
                  "Confirm taxis use the meter or a trusted app"],
        )
