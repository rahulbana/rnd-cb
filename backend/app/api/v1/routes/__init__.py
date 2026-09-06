"""Versioned API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import documents, health, jobs, retrieve

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(retrieve.router)

__all__ = ["api_router"]
