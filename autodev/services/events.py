"""Persist-and-publish event helper used throughout the agent run.

Every meaningful step calls :func:`emit`, which (1) writes an ``Event`` row
with a monotonically increasing per-project ``seq`` and (2) broadcasts it to
live subscribers. This dual write is what makes runs resumable across app
restarts: the DB is the source of truth, the bus is just the live tap.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select

from ..database import session_scope
from ..models import Event
from .event_bus import bus


async def emit(
    project_id: str,
    type: str,
    message: str = "",
    *,
    phase: str = "",
    level: str = "info",
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Persist an event and broadcast it. Returns the serialized event."""
    with session_scope() as session:
        max_seq = session.execute(
            select(func.coalesce(func.max(Event.seq), 0)).where(
                Event.project_id == project_id
            )
        ).scalar_one()
        event = Event(
            project_id=project_id,
            seq=int(max_seq) + 1,
            type=type,
            phase=phase,
            level=level,
            message=message,
            data=data,
        )
        session.add(event)
        session.flush()
        payload = event.to_dict()

    await bus.publish(project_id, payload)
    return payload
