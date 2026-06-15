"""Aggregate API router mounted under /api."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health, study_plans

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(study_plans.router)
