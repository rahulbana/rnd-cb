"""Versioned API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import admin, auth, chat, documents, health, jobs, retrieve

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(retrieve.router)
api_router.include_router(chat.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
