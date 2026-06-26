"""Prometheus metrics exposition endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Response

from ...observability.metrics import render_latest

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def metrics() -> Response:
    payload, content_type = render_latest()
    return Response(content=payload, media_type=content_type)
