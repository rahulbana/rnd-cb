"""Aggregate API router."""
from __future__ import annotations

from fastapi import APIRouter

from .routes import health, runs, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
api_router.include_router(runs.router)
