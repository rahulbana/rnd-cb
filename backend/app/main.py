"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import resume

settings = get_settings()

app = FastAPI(
    title="AI Resume/CV Generator",
    description=(
        "Turn raw career information into a polished, structured resume and "
        "download it as a styled PDF."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "AI Resume/CV Generator",
        "docs": "/docs",
        "health": "/api/health",
    }
