"""Trip service — application logic tying persistence, the orchestrator and
observability together."""
from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from ..config.logging import get_logger
from ..orchestration.orchestrator import EventSink
from ..repositories import observability_repository, trip_repository
from ..schemas.agents import AgentResult
from ..schemas.trip import TripCreate, TripState, TripStatus, TripSummary
from .engine import get_orchestrator, get_runtime

logger = get_logger(__name__)


class TripNotFound(Exception):
    pass


def create_trip(session: Session, payload: TripCreate, user_id: str | None) -> TripState:
    title = payload.title or _title_from_request(payload)
    state = TripState(
        user_id=UUID(user_id) if user_id else None,
        title=title,
        request=payload.request,
    )
    trip_repository.create(session, state, user_id)
    return state


def get_trip(session: Session, trip_id: UUID, user_id: str | None) -> TripState:
    state = trip_repository.get_state(session, trip_id, user_id)
    if state is None:
        raise TripNotFound(str(trip_id))
    return state


def list_trips(session: Session, user_id: str | None) -> list[TripSummary]:
    return trip_repository.list_summaries(session, user_id)


def delete_trip(session: Session, trip_id: UUID, user_id: str | None) -> bool:
    return trip_repository.soft_delete(session, trip_id, user_id)


async def plan_trip(session: Session, trip_id: UUID, user_id: str | None,
                    sink: EventSink | None = None) -> TripState:
    state = get_trip(session, trip_id, user_id)
    orchestrator = get_orchestrator()
    results = await orchestrator.plan_trip(state, sink)
    _persist(session, state, user_id, results)
    return state


async def optimize_trip(session: Session, trip_id: UUID, user_id: str | None,
                        sink: EventSink | None = None) -> TripState:
    state = get_trip(session, trip_id, user_id)
    orchestrator = get_orchestrator()
    results = await orchestrator.run_agents(state, ["activity", "budget", "itinerary"], sink)
    _persist(session, state, user_id, results)
    return state


async def run_single_agent(session: Session, trip_id: UUID, agent_name: str,
                           user_id: str | None) -> tuple[TripState, list[AgentResult]]:
    state = get_trip(session, trip_id, user_id)
    orchestrator = get_orchestrator()
    results = await orchestrator.run_agents(state, [agent_name])
    _persist(session, state, user_id, results)
    return state, results


def save_state(session: Session, state: TripState, user_id: str | None) -> TripState:
    trip_repository.save(session, state, user_id)
    return state


def _persist(session: Session, state: TripState, user_id: str | None,
             results: list[AgentResult]) -> None:
    trip_repository.save(session, state, user_id)
    model = "mock" if get_runtime().offline else "openai"
    try:
        observability_repository.record_runs(
            session, trip_id=str(state.trip_id), run_id=str(uuid.uuid4()),
            results=results, model=model,
        )
    except Exception as exc:  # observability must never break the request
        logger.warning("failed to record agent runs: %s", exc)


def _title_from_request(payload: TripCreate) -> str:
    dests = payload.request.destinations
    if dests:
        return f"Trip to {', '.join(dests[:2])}"
    return "New trip"
