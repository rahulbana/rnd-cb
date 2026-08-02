"""Pydantic request/response models for the chat API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """A chat turn. ``messages`` carries prior turns for conversational context."""

    messages: list[ChatMessage] = Field(..., min_length=1)

    def latest_user_message(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        raise ValueError("No user message present in the request.")


class ToolCallEvent(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model: str
    mcp_server: str
    tools: list[str]
