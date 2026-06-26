"""Search endpoint: runs the agent and streams progress over SSE."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...schemas.search import SearchRequest
from ..deps import SearchServiceDep

router = APIRouter(tags=["search"])


def _sse(event: dict) -> str:
    """Format a dict as a Server-Sent Event frame."""
    return f"data: {json.dumps(event)}\n\n"


@router.post("/search")
async def search(req: SearchRequest, service: SearchServiceDep) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        async for event in service.stream(req.query, req.num_subqueries):
            yield _sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
