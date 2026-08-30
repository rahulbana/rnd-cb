"""Merge validated agent results into the shared TripState.

Kept separate from agents so that agents stay pure (no state mutation) and the
merge rules are tested in one place.
"""
from __future__ import annotations

from ..config.logging import get_logger
from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.trip import BudgetBreakdown, ItineraryDay, Place, TripState

logger = get_logger(__name__)


def _places_from_recs(items: list[dict]) -> list[Place]:
    places: list[Place] = []
    for it in items:
        places.append(Place(
            name=it.get("name", "Unknown"),
            category=it.get("category", "attraction"),
            recommendation=it.get("recommendation"),
            est_cost=it.get("est_cost"),
            duration_minutes=it.get("duration_minutes"),
            note=it.get("why") or it.get("note"),
            tags=[it["neighborhood"]] if it.get("neighborhood") else [],
        ))
    return places


def merge_result(trip: TripState, result: AgentResult) -> None:
    if result.status in (AgentStatus.FAILED, AgentStatus.SKIPPED):
        if result.warnings:
            trip.warnings.extend(result.warnings)
        return

    data = result.data
    try:
        match result.agent:
            case "destination":
                trip.destination_overview = data
            case "flight":
                trip.flights = data
            case "hotel":
                trip.accommodation = data
            case "activity":
                trip.activities = _places_from_recs(data.get("items", []))
            case "food":
                trip.restaurants = _places_from_recs(data.get("items", []))
            case "weather":
                trip.weather = data
            case "itinerary":
                trip.itinerary = [ItineraryDay.model_validate(d) for d in data.get("itinerary", [])]
            case "transportation":
                trip.transportation = data
            case "budget":
                trip.budget = BudgetBreakdown.model_validate(data)
            case "visa":
                trip.visa = data
            case "safety":
                trip.safety = data
            case "packing":
                trip.packing = data.get("items", [])
            case "local_guide":
                trip.local_tips = data
            case _:
                logger.warning("no merge rule for agent %s", result.agent)
    except Exception as exc:  # never let a bad payload corrupt the trip
        logger.warning("merge failed for %s: %s", result.agent, exc)
        trip.warnings.append(f"Could not integrate {result.agent} results.")

    trip.warnings.extend(result.warnings)
    trip.touch()
