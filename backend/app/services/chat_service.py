"""Chat service — the context-aware travel assistant (spec section 15).

The assistant is grounded in the current TripState (itinerary, budget, weather,
preferences) so it behaves like a travel agent, not a generic chatbot. It
routes single-topic questions to the matching agent and answers conversationally.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ..llm import TaskComplexity
from ..orchestration.intent import Intent, detect_intent
from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.trip import TripState
from .engine import get_orchestrator, get_runtime
from .trip_service import get_trip, save_state


def _trip_context(trip: TripState | None) -> str:
    if trip is None:
        return "No trip is currently selected."
    req = trip.request
    lines = [f"Trip: {trip.title} (status: {trip.status.value})"]
    if req.destinations:
        lines.append(f"Destinations: {', '.join(req.destinations)}")
    if req.duration_days:
        lines.append(f"Duration: {req.duration_days} days, {req.travelers} traveller(s)")
    if req.budget:
        lines.append(f"Budget: {req.budget.amount:.0f} {req.budget.currency}")
    if trip.budget and trip.budget.total_comfort:
        lines.append(f"Estimated comfort cost: {trip.budget.total_comfort.amount:.0f} {trip.budget.currency}")
    if trip.itinerary:
        lines.append(f"Itinerary spans {len(trip.itinerary)} day(s).")
    if trip.weather:
        w = trip.weather
        lines.append(f"Weather: {w.get('season')} ~{w.get('typical_low_c')}-{w.get('typical_high_c')}C")
    if req.preferences.interests:
        lines.append(f"Interests: {', '.join(req.preferences.interests)}")
    return "\n".join(lines)


async def handle_chat(session: Session, payload: ChatRequest, user_id: str | None) -> ChatResponse:
    trip: TripState | None = None
    if payload.trip_id:
        try:
            trip = get_trip(session, payload.trip_id, user_id)
        except Exception:
            trip = None

    intent = detect_intent(payload.message)
    used_agents: list[str] = []

    # For actionable single-topic intents on a real trip, run the agent so the
    # answer is grounded in fresh structured data.
    orchestrator = get_orchestrator()
    from ..orchestration.intent import INTENT_TO_AGENT
    if trip is not None and intent.intent in INTENT_TO_AGENT:
        agent = INTENT_TO_AGENT[intent.intent]
        results = await orchestrator.run_agents(trip, [agent])
        used_agents = [r.agent for r in results]
        save_state(session, trip, user_id)

    runtime = get_runtime()
    system = (
        "You are a helpful, context-aware travel assistant. Use the trip context to "
        "answer specifically and practically. Be concise. Never invent live prices or "
        "availability; frame estimates clearly. If information is missing, say so."
    )
    user = (
        f"Trip context:\n{_trip_context(trip)}\n\n"
        f"User question: {payload.message}"
    )
    fallback = _offline_reply(intent.intent, trip)
    reply, _usage = await runtime.generate_text(
        system=system, user=user, complexity=TaskComplexity.MODERATE, fallback=fallback,
    )
    return ChatResponse(
        reply=reply,
        intent=intent.intent.value,
        used_agents=used_agents,
        suggestions=_suggestions(intent.intent),
    )


def _offline_reply(intent: Intent, trip: TripState | None) -> str:
    base = "You're in offline mode (no AI model configured), so here's a grounded summary:\n\n"
    ctx = _trip_context(trip)
    hint = {
        Intent.BUDGET: "See the Budget tab for the min/comfort/premium breakdown.",
        Intent.WEATHER: "See the Weather section for the seasonal outlook.",
        Intent.ITINERARY: "See the Itinerary tab for the day-by-day plan.",
        Intent.PLAN_TRIP: "Use 'Plan trip' to run all agents and build the full plan.",
    }.get(intent, "Set OPENAI_API_KEY to enable full conversational answers.")
    return base + ctx + "\n\n" + hint


def _suggestions(intent: Intent) -> list[str]:
    if intent is Intent.PLAN_TRIP:
        return ["Make this trip cheaper", "Optimize my itinerary", "What can I do if it rains?"]
    return ["Show me the budget breakdown", "Suggest more activities", "Any safety tips?"]
