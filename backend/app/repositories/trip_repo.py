"""Trip repository — persists the TripState aggregate as a JSON document."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.tables import Trip
from ..schemas.trip import TripState, TripSummary


class TripRepository:
    def create(self, session: Session, state: TripState, user_id: str | None = None) -> Trip:
        row = Trip(
            id=str(state.trip_id),
            user_id=user_id,
            title=state.title,
            status=state.status.value,
            state=state.model_dump(mode="json"),
        )
        session.add(row)
        session.flush()
        return row

    def save(self, session: Session, state: TripState, user_id: str | None = None) -> Trip:
        row = session.get(Trip, str(state.trip_id))
        if row is None:
            return self.create(session, state, user_id)
        state.touch()
        row.title = state.title
        row.status = state.status.value
        row.state = state.model_dump(mode="json")
        session.flush()
        return row

    def get_state(self, session: Session, trip_id: UUID | str, user_id: str | None = None) -> TripState | None:
        row = session.get(Trip, str(trip_id))
        if row is None or row.is_deleted:
            return None
        if user_id is not None and row.user_id not in (None, user_id):
            return None  # data isolation (spec section 27)
        return TripState.model_validate(row.state)

    def list_summaries(self, session: Session, user_id: str | None = None) -> list[TripSummary]:
        stmt = select(Trip).where(Trip.is_deleted.is_(False)).order_by(Trip.updated_at.desc())
        if user_id is not None:
            stmt = stmt.where((Trip.user_id == user_id) | (Trip.user_id.is_(None)))
        summaries: list[TripSummary] = []
        for row in session.scalars(stmt):
            state = TripState.model_validate(row.state)
            req = state.request
            summaries.append(TripSummary(
                trip_id=state.trip_id, title=state.title, status=state.status,
                destinations=req.destinations, start_date=req.start_date,
                duration_days=req.duration_days, travelers=req.travelers,
                updated_at=row.updated_at,
            ))
        return summaries

    def soft_delete(self, session: Session, trip_id: UUID | str, user_id: str | None = None) -> bool:
        row = session.get(Trip, str(trip_id))
        if row is None or row.is_deleted:
            return False
        if user_id is not None and row.user_id not in (None, user_id):
            return False
        row.is_deleted = True
        session.flush()
        return True


trip_repository = TripRepository()
