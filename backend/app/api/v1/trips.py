"""Trip CRUD and natural-language trip creation."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...models.db import get_session
from ...schemas.trip import TripCreate, TripRequest, TripState, TripSummary
from ...security import get_optional_user_id
from ...services import parse_trip_request, trip_service
from ...services.trip_service import TripNotFound

router = APIRouter(prefix="/trips", tags=["trips"])


class NLTripRequest(BaseModel):
    text: str


@router.post("/parse", response_model=TripRequest)
def parse(payload: NLTripRequest) -> TripRequest:
    """Convert a natural-language prompt into structured trip requirements (section 16)."""
    return parse_trip_request(payload.text)


@router.post("", response_model=TripState, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, session: Session = Depends(get_session),
                user_id: str | None = Depends(get_optional_user_id)) -> TripState:
    return trip_service.create_trip(session, payload, user_id)


@router.post("/from-text", response_model=TripState, status_code=status.HTTP_201_CREATED)
def create_from_text(payload: NLTripRequest, session: Session = Depends(get_session),
                     user_id: str | None = Depends(get_optional_user_id)) -> TripState:
    req = parse_trip_request(payload.text)
    return trip_service.create_trip(session, TripCreate(request=req), user_id)


@router.get("", response_model=list[TripSummary])
def list_trips(session: Session = Depends(get_session),
               user_id: str | None = Depends(get_optional_user_id)) -> list[TripSummary]:
    return trip_service.list_trips(session, user_id)


@router.get("/{trip_id}", response_model=TripState)
def get_trip(trip_id: UUID, session: Session = Depends(get_session),
             user_id: str | None = Depends(get_optional_user_id)) -> TripState:
    try:
        return trip_service.get_trip(session, trip_id, user_id)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")


class TripPatch(BaseModel):
    title: str | None = None
    request: TripRequest | None = None


@router.patch("/{trip_id}", response_model=TripState)
def update_trip(trip_id: UUID, patch: TripPatch, session: Session = Depends(get_session),
                user_id: str | None = Depends(get_optional_user_id)) -> TripState:
    try:
        state = trip_service.get_trip(session, trip_id, user_id)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if patch.title is not None:
        state.title = patch.title
    if patch.request is not None:
        state.request = patch.request
    return trip_service.save_state(session, state, user_id)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: UUID, session: Session = Depends(get_session),
                user_id: str | None = Depends(get_optional_user_id)) -> None:
    if not trip_service.delete_trip(session, trip_id, user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
