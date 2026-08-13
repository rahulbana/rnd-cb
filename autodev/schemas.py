"""Pydantic request/response schemas for the HTTP API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    goal: str = Field(..., min_length=3, description="What to build")
    name: Optional[str] = None
    auto_start: bool = True


class SimpleOk(BaseModel):
    ok: bool = True
    detail: str = ""
