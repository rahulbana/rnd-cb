"""Orchestrator + agent integration tests (spec sections 7-9)."""
from datetime import date

import pytest

from app.orchestration import Orchestrator
from app.orchestration.orchestrator import FULL_PLAN_AGENTS
from app.schemas.common import Money, TravelerType
from app.schemas.trip import TripRequest, TripState, TripStatus


def _trip() -> TripState:
    req = TripRequest(
        origin="Delhi", destinations=["Tokyo"], duration_days=5, travelers=2,
        traveler_type=TravelerType.COUPLE, budget=Money(amount=250000, currency="INR"),
        start_date=date(2026, 10, 5),
    )
    req.preferences.interests = ["food", "culture", "photography"]
    return TripState(title="Japan", request=req)


def test_layering_orders_dependencies():
    orch = Orchestrator()
    layers = orch._layer(FULL_PLAN_AGENTS)
    flat = [a for layer in layers for a in layer]
    # itinerary must come after activity + destination.
    assert flat.index("itinerary") > flat.index("activity")
    assert flat.index("itinerary") > flat.index("destination")
    # budget after its dependencies.
    assert flat.index("budget") > flat.index("activity")
    # packing after weather.
    assert flat.index("packing") > flat.index("weather")


@pytest.mark.asyncio
async def test_full_plan_populates_state():
    trip = _trip()
    results = await Orchestrator().plan_trip(trip)
    assert trip.status is TripStatus.PLANNED
    assert len(results) == len(FULL_PLAN_AGENTS)
    assert len(trip.itinerary) == 5
    assert trip.activities and trip.restaurants
    assert trip.budget and trip.budget.total_comfort
    assert trip.weather and trip.packing
    assert trip.highlights  # synthesis produced highlights


@pytest.mark.asyncio
async def test_budget_feasibility_flag_set():
    trip = _trip()
    trip.request.budget = Money(amount=1000, currency="INR")  # absurdly low
    await Orchestrator().plan_trip(trip)
    assert trip.budget.within_budget is False
    assert any("budget" in w.lower() for w in trip.warnings)


@pytest.mark.asyncio
async def test_flight_skipped_without_origin():
    trip = _trip()
    trip.request.origin = None
    results = await Orchestrator().run_agents(trip, ["flight"])
    assert results[0].status.value == "skipped"
