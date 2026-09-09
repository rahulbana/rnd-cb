"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """Lightweight conversation representation for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    system_prompt: str
    temperature: float
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)


class ConversationUpdate(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)


class ChatRequest(BaseModel):
    content: str = Field(min_length=1)


class UserInfo(BaseModel):
    username: str
    model: str
    temperature_supported: bool
