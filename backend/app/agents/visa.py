"""Visa & Documentation Agent (spec section 8). Always flags official verification."""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus, VisaInfo
from ..schemas.common import DataPoint, DataTrust
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class VisaAgent(BaseAgent):
    name = "visa"
    description = "Visa/passport/entry requirements — always marked for official verification."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        origin = req.origin or "your country"
        system = (
            f"{GUARDRAILS} You are a travel-documentation assistant. Summarise likely visa/entry "
            "requirements and passport validity, and list documents to prepare. ALWAYS include a "
            "disclaimer that requirements must be verified with official sources."
        )
        user = f"Traveller nationality/origin: {origin}. Destination: {dest}.\n{request_brief(req)}"
        info, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=VisaInfo,
            fallback=lambda: VisaInfo(
                destination=dest,
                requirement="Requirements vary by nationality — verify officially.",
                passport_validity="Commonly 6 months beyond travel dates.",
                documents=["Valid passport", "Return/onward ticket", "Proof of accommodation",
                           "Travel insurance (recommended)"],
            ),
        )
        return self._result(
            status=AgentStatus.OK if used_llm else AgentStatus.PARTIAL,
            summary=f"Visa/entry guidance for {dest} (verify officially).",
            data=info.model_dump(),
            citations=[DataPoint(value="Visa guidance requires official verification",
                                 source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.3)],
            warnings=["Immigration rules change frequently — confirm with the official embassy/consulate."],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )
