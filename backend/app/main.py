"""FastAPI application factory and entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, dashboards, me, organizations, users
from app.core.config import get_settings
from app.core.database import init_db
from app.seed import ensure_superadmin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_superadmin()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Multi-tenant RBAC platform: superadmins manage organizations and "
        "users; org admins manage dashboards and access; developers and "
        "viewers work within dashboards."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


api_prefix = "/api"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(me.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(organizations.router, prefix=api_prefix)
app.include_router(dashboards.router, prefix=api_prefix)
