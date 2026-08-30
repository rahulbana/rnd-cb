"""Local Guide Agent (spec section 8) — currency, tipping, etiquette, phrases, apps."""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus, LocalTips
from ..schemas.common import DataPoint, DataTrust
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class LocalGuideAgent(BaseAgent):
    name = "local_guide"
    description = "Local etiquette, currency, tipping, phrases and useful apps."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        currency = req.budget.currency if req.budget else "local currency"
        system = (
            f"{GUARDRAILS} You are a friendly local guide. Share currency, tipping norms, key "
            "etiquette, a handful of useful local phrases (with English meaning) and a few helpful apps."
        )
        user = f"Give local tips.\n{request_brief(req)}"
        tips, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=LocalTips,
            fallback=lambda: LocalTips(
                destination=dest, currency=currency,
                tipping="Tipping norms vary — check locally; rounding up is common.",
                etiquette=["Dress respectfully at religious sites", "Queue politely",
                           "Ask before photographing people"],
                phrases={"Hello": "(local greeting)", "Thank you": "(local thanks)",
                         "How much?": "(local phrase)"},
                useful_apps=["Offline maps", "A local transit app", "A translation app"],
            ),
        )
        return self._result(
            status=AgentStatus.OK if used_llm else AgentStatus.PARTIAL,
            summary=f"Local tips for {dest}.",
            data=tips.model_dump(),
            citations=[DataPoint(value="Local etiquette & tips", source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.4)],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )
