"""Centralised exception handling -> consistent JSON error envelopes."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger

log = get_logger("api.errors")


def _envelope(error_type: str, message: str) -> dict:
    return {"error": {"type": error_type, "message": message}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.warning("%s on %s: %s", exc.error_type, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.error_type, exc.message),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=_envelope("internal_error", "An unexpected error occurred."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
