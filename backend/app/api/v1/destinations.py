"""Ad-hoc destination research endpoint (no trip required)."""
from __future__ import annotations

from fastapi import APIRouter

from ...schemas.agents import DestinationOverview
from ...schemas.trip import TripRequest, TripState
from ...services.engine import get_orchestrator

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("/{destination}")
async def research_destination(destination: str) -> dict:
    """Run the destination agent standalone for a quick overview."""
    trip = TripState(title=f"Research: {destination}",
                     request=TripRequest(destinations=[destination]))
    results = await get_orchestrator().run_agents(trip, ["destination", "weather", "safety", "local_guide"])
    return {
        "destination": destination,
        "overview": trip.destination_overview,
        "weather": trip.weather,
        "safety": trip.safety,
        "local_tips": trip.local_tips,
        "agents": [{"agent": r.agent, "status": r.status.value} for r in results],
    }
