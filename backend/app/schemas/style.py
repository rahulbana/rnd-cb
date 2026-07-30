"""Schemas for writing-style reference material."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StyleLinkCreate(BaseModel):
    url: str = Field(..., description="Public http(s) URL of previous writing")


class StyleReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_type: str
    origin: str
    char_count: int
    created_at: datetime
