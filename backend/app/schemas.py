"""Pydantic models for API payloads and the WebSocket protocol."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ToolCallRecord(BaseModel):
    id: str
    name: str
    arguments: str  # raw JSON string as returned by the model


class ChatMessage(BaseModel):
    id: str
    conversationId: str
    role: Role
    content: str
    toolCalls: Optional[list[ToolCallRecord]] = None
    toolCallId: Optional[str] = None
    name: Optional[str] = None
    createdAt: str


class Conversation(BaseModel):
    id: str
    title: str
    projectPath: Optional[str] = None
    createdAt: str
    updatedAt: str


class AppSettings(BaseModel):
    projectPath: Optional[str] = None
    model: str
    permissionMode: Literal["ask", "auto"]
    hasApiKey: bool
    dbConnected: bool


class ModelUpdate(BaseModel):
    model: str


class PermissionModeUpdate(BaseModel):
    mode: Literal["ask", "auto"]


class ProjectPathUpdate(BaseModel):
    path: str


class CreateProjectRequest(BaseModel):
    parentPath: str
    name: str
    createVenv: bool = True


class CreateProjectResponse(BaseModel):
    settings: AppSettings
    projectPath: str
    venvCreated: bool = False
    venvMessage: str = ""


# ---- WebSocket client -> server messages ----
class RunMessage(BaseModel):
    type: Literal["run"] = "run"
    conversationId: Optional[str] = None
    prompt: str


class ApprovalMessage(BaseModel):
    type: Literal["approval"] = "approval"
    id: str
    approved: bool


class CancelMessage(BaseModel):
    type: Literal["cancel"] = "cancel"
    conversationId: str


class ApprovalRequest(BaseModel):
    id: str
    tool: str
    summary: str
    details: str = ""
