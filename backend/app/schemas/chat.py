"""Chat / assistant schemas."""
from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    trip_id: UUID | None = None
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    used_agents: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class StreamEvent(BaseModel):
    """A server-sent event emitted while planning/chatting (spec section 25)."""

    type: str  # status | agent_started | agent_done | token | result | error | done
    message: str = ""
    agent: str | None = None
    data: dict | None = None
