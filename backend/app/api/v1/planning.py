"""Planning, optimization, itinerary and derived-view endpoints (incl. SSE)."""
from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...models.db import get_session
from ...schemas.chat import StreamEvent
from ...schemas.trip import BudgetBreakdown, ItineraryDay, TripState
from ...security import get_optional_user_id
from ...services import trip_service
from ...services.engine import get_orchestrator
from ...services.trip_service import TripNotFound

router = APIRouter(prefix="/trips", tags=["planning"])


def _sse(event: StreamEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


@router.post("/{trip_id}/plan", response_model=TripState)
async def plan(trip_id: UUID, session: Session = Depends(get_session),
               user_id: str | None = Depends(get_optional_user_id)) -> TripState:
    try:
        return await trip_service.plan_trip(session, trip_id, user_id)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")


@router.post("/{trip_id}/plan/stream")
async def plan_stream(trip_id: UUID, session: Session = Depends(get_session),
                      user_id: str | None = Depends(get_optional_user_id)) -> StreamingResponse:
    try:
        trip_service.get_trip(session, trip_id, user_id)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")

    queue: asyncio.Queue[StreamEvent] = asyncio.Queue()

    async def sink(event: StreamEvent) -> None:
        await queue.put(event)

    async def runner() -> None:
        try:
            state = await trip_service.plan_trip(session, trip_id, user_id, sink)
            await queue.put(StreamEvent(type="result", message="Trip plan ready",
                                        data=state.model_dump(mode="json")))
        except Exception as exc:  # surface a safe error to the client
            await queue.put(StreamEvent(type="error", message=str(exc)))
        finally:
            await queue.put(StreamEvent(type="done", message="Complete"))

    async def gen():
        task = asyncio.create_task(runner())
        yield _sse(StreamEvent(type="status", message="Planning your trip…"))
        while True:
            event = await queue.get()
            yield _sse(event)
            if event.type == "done":
                break
        await task

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{trip_id}/optimize", response_model=TripState)
async def optimize(trip_id: UUID, session: Session = Depends(get_session),
                   user_id: str | None = Depends(get_optional_user_id)) -> TripState:
    try:
        return await trip_service.optimize_trip(session, trip_id, user_id)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")


@router.get("/{trip_id}/itinerary", response_model=list[ItineraryDay])
def get_itinerary(trip_id: UUID, session: Session = Depends(get_session),
                  user_id: str | None = Depends(get_optional_user_id)) -> list[ItineraryDay]:
    return _load(session, trip_id, user_id).itinerary


class ItineraryUpdate(BaseModel):
    itinerary: list[ItineraryDay]


@router.patch("/{trip_id}/itinerary", response_model=list[ItineraryDay])
def update_itinerary(trip_id: UUID, payload: ItineraryUpdate,
                     session: Session = Depends(get_session),
                     user_id: str | None = Depends(get_optional_user_id)) -> list[ItineraryDay]:
    """Persist a reordered/edited itinerary (drag-and-drop — spec section 14)."""
    state = _load(session, trip_id, user_id)
    state.itinerary = payload.itinerary
    trip_service.save_state(session, state, user_id)
    return state.itinerary


@router.get("/{trip_id}/budget", response_model=BudgetBreakdown | None)
def get_budget(trip_id: UUID, session: Session = Depends(get_session),
               user_id: str | None = Depends(get_optional_user_id)) -> BudgetBreakdown | None:
    return _load(session, trip_id, user_id).budget


@router.get("/{trip_id}/weather")
def get_weather(trip_id: UUID, session: Session = Depends(get_session),
                user_id: str | None = Depends(get_optional_user_id)) -> dict | None:
    return _load(session, trip_id, user_id).weather


@router.get("/{trip_id}/map")
async def get_map(trip_id: UUID, session: Session = Depends(get_session),
                  user_id: str | None = Depends(get_optional_user_id)) -> dict:
    """Return geocoded points for the trip (spec section 13)."""
    state = _load(session, trip_id, user_id)
    tools = get_orchestrator().tools
    points: list[dict] = []
    for dest in state.request.destinations:
        res = await tools.execute("geocode", query=dest)
        if res.ok:
            points.append({"name": dest, "kind": "destination",
                           "lat": res.data["lat"], "lng": res.data["lng"]})
    center = points[0] if points else None
    return {"center": center, "points": points}


def _load(session: Session, trip_id: UUID, user_id: str | None) -> TripState:
    try:
        return trip_service.get_trip(session, trip_id, user_id)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
