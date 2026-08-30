"""Shared helpers for agents: prompt scaffolding and request summarisation."""
from __future__ import annotations

from ..schemas.trip import TripRequest

GUARDRAILS = (
    "You are a specialist travel agent. Be concrete, realistic and concise. "
    "Never fabricate live availability, prices or current weather — give clearly "
    "framed estimates instead. Respect the traveller's budget and preferences. "
    "Consider travel time and opening hours. Prefer well-known, verifiable facts."
)


def primary_destination(req: TripRequest) -> str:
    if req.destinations:
        return req.destinations[0]
    return "the destination"


def request_brief(req: TripRequest) -> str:
    parts: list[str] = []
    if req.origin:
        parts.append(f"Origin: {req.origin}")
    if req.destinations:
        parts.append(f"Destinations: {', '.join(req.destinations)}")
    if req.duration_days:
        parts.append(f"Duration: {req.duration_days} days")
    if req.start_date:
        parts.append(f"Start: {req.start_date.isoformat()}")
    parts.append(f"Travellers: {req.travelers} ({req.traveler_type.value})")
    if req.budget:
        parts.append(f"Budget: {req.budget.amount:.0f} {req.budget.currency}")
    prefs = req.preferences
    parts.append(f"Style: {prefs.travel_style.value}")
    if prefs.interests:
        parts.append(f"Interests: {', '.join(prefs.interests)}")
    if prefs.dietary:
        parts.append(f"Dietary: {', '.join(prefs.dietary)}")
    if prefs.accessibility_needs:
        parts.append(f"Accessibility: {', '.join(prefs.accessibility_needs)}")
    if req.notes:
        parts.append(f"Notes: {req.notes}")
    return "\n".join(parts)


def month_of(req: TripRequest) -> int | None:
    return req.start_date.month if req.start_date else None
