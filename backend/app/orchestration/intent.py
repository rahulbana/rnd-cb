"""Intent detection (spec section 9 — deterministic + LLM hybrid).

A fast deterministic keyword classifier handles the common cases; the result
carries a confidence so the orchestrator can decide when to escalate to the
LLM. We never let the LLM *silently* decide everything.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    PLAN_TRIP = "plan_trip"
    OPTIMIZE = "optimize"
    DESTINATION = "destination"
    FLIGHT = "flight"
    HOTEL = "hotel"
    ITINERARY = "itinerary"
    TRANSPORT = "transportation"
    FOOD = "food"
    ACTIVITY = "activity"
    BUDGET = "budget"
    WEATHER = "weather"
    VISA = "visa"
    SAFETY = "safety"
    PACKING = "packing"
    LOCAL = "local_guide"
    GENERAL = "general"


# Single-topic intents map directly to one agent.
INTENT_TO_AGENT: dict[Intent, str] = {
    Intent.DESTINATION: "destination",
    Intent.FLIGHT: "flight",
    Intent.HOTEL: "hotel",
    Intent.ITINERARY: "itinerary",
    Intent.TRANSPORT: "transportation",
    Intent.FOOD: "food",
    Intent.ACTIVITY: "activity",
    Intent.BUDGET: "budget",
    Intent.WEATHER: "weather",
    Intent.VISA: "visa",
    Intent.SAFETY: "safety",
    Intent.PACKING: "packing",
    Intent.LOCAL: "local_guide",
}

_KEYWORDS: list[tuple[Intent, tuple[str, ...]]] = [
    (Intent.PLAN_TRIP, ("plan a trip", "plan my trip", "plan a", "full trip", "where should i go",
                        "complete trip", "plan our", "organize a trip", "itinerary for")),
    (Intent.OPTIMIZE, ("optimize", "cheaper", "reduce cost", "reduce my", "make this", "shorten",
                       "too expensive", "save money")),
    (Intent.WEATHER, ("weather", "rain", "temperature", "forecast", "climate")),
    (Intent.FLIGHT, ("flight", "fly", "airfare", "airport", "airline")),
    (Intent.HOTEL, ("hotel", "stay", "accommodation", "hostel", "airbnb", "where to stay")),
    (Intent.VISA, ("visa", "passport", "entry requirement", "documents required")),
    (Intent.SAFETY, ("safe", "safety", "scam", "dangerous", "emergency number")),
    (Intent.PACKING, ("pack", "packing", "what to bring", "what to wear")),
    (Intent.BUDGET, ("budget", "cost", "how much", "expensive", "afford", "price")),
    (Intent.FOOD, ("food", "eat", "restaurant", "cuisine", "vegetarian", "vegan", "dinner", "lunch")),
    (Intent.TRANSPORT, ("get around", "transport", "metro", "subway", "taxi", "train", "bus")),
    (Intent.ACTIVITY, ("things to do", "activities", "attractions", "sightsee", "see", "visit", "tour", "museum")),
    (Intent.ITINERARY, ("itinerary", "schedule", "day by day", "plan the day", "each day")),
    (Intent.LOCAL, ("tipping", "etiquette", "phrases", "customs", "currency", "local tips")),
    (Intent.DESTINATION, ("about", "overview", "best time", "tell me about", "hidden gems", "neighborhood")),
]


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    matched: str | None = None


def detect_intent(text: str) -> IntentResult:
    t = f" {text.lower().strip()} "
    for intent, phrases in _KEYWORDS:
        for phrase in phrases:
            if phrase in t:
                # Multi-agent planning phrases are higher confidence.
                conf = 0.85 if intent in (Intent.PLAN_TRIP, Intent.OPTIMIZE) else 0.7
                return IntentResult(intent=intent, confidence=conf, matched=phrase)
    return IntentResult(intent=Intent.GENERAL, confidence=0.3)
