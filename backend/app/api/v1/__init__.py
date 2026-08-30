"""API v1 router aggregation."""
from fastapi import APIRouter

from . import auth, chat, destinations, health, planning, trips

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(trips.router)
api_router.include_router(planning.router)
api_router.include_router(chat.router)
api_router.include_router(destinations.router)

__all__ = ["api_router"]
