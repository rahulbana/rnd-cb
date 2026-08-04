"""CRUD for conversations and messages, with an in-memory fallback."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from . import db
from .schemas import ChatMessage, Conversation, Role, ToolCallRecord

# In-memory fallback so the app is usable without Postgres.
_mem_conversations: dict[str, Conversation] = {}
_mem_messages: dict[str, list[ChatMessage]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


async def create_conversation(project_path: str | None, title: str = "New conversation") -> Conversation:
    cid = _new_id()
    conv = Conversation(
        id=cid,
        title=title,
        projectPath=project_path,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )
    if db.is_connected():
        await db.get_pool().execute(  # type: ignore[union-attr]
            """INSERT INTO conversations (id, title, project_path, created_at, updated_at)
               VALUES ($1, $2, $3, now(), now())""",
            uuid.UUID(cid),
            title,
            project_path,
        )
    else:
        _mem_conversations[cid] = conv
        _mem_messages[cid] = []
    return conv


async def rename_conversation(cid: str, title: str) -> None:
    if db.is_connected():
        await db.get_pool().execute(  # type: ignore[union-attr]
            "UPDATE conversations SET title = $2, updated_at = now() WHERE id = $1",
            uuid.UUID(cid),
            title,
        )
    elif cid in _mem_conversations:
        _mem_conversations[cid].title = title
        _mem_conversations[cid].updatedAt = _now_iso()


async def touch_conversation(cid: str) -> None:
    if db.is_connected():
        await db.get_pool().execute(  # type: ignore[union-attr]
            "UPDATE conversations SET updated_at = now() WHERE id = $1",
            uuid.UUID(cid),
        )
    elif cid in _mem_conversations:
        _mem_conversations[cid].updatedAt = _now_iso()


async def list_conversations() -> list[Conversation]:
    if db.is_connected():
        rows = await db.get_pool().fetch(  # type: ignore[union-attr]
            """SELECT id, title, project_path, created_at, updated_at
               FROM conversations ORDER BY updated_at DESC"""
        )
        return [_row_to_conversation(r) for r in rows]
    return sorted(_mem_conversations.values(), key=lambda c: c.updatedAt, reverse=True)


async def delete_conversation(cid: str) -> None:
    if db.is_connected():
        await db.get_pool().execute(  # type: ignore[union-attr]
            "DELETE FROM conversations WHERE id = $1", uuid.UUID(cid)
        )
    else:
        _mem_conversations.pop(cid, None)
        _mem_messages.pop(cid, None)


async def add_message(
    conversation_id: str,
    role: Role,
    content: str,
    tool_calls: list[ToolCallRecord] | None = None,
    tool_call_id: str | None = None,
    name: str | None = None,
) -> ChatMessage:
    mid = _new_id()
    record = ChatMessage(
        id=mid,
        conversationId=conversation_id,
        role=role,
        content=content,
        toolCalls=tool_calls,
        toolCallId=tool_call_id,
        name=name,
        createdAt=_now_iso(),
    )
    if db.is_connected():
        await db.get_pool().execute(  # type: ignore[union-attr]
            """INSERT INTO messages
                 (id, conversation_id, role, content, tool_calls, tool_call_id, name, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, now())""",
            uuid.UUID(mid),
            uuid.UUID(conversation_id),
            role,
            content,
            json.dumps([tc.model_dump() for tc in tool_calls]) if tool_calls else None,
            tool_call_id,
            name,
        )
    else:
        _mem_messages.setdefault(conversation_id, []).append(record)
    return record


async def get_messages(conversation_id: str) -> list[ChatMessage]:
    if db.is_connected():
        rows = await db.get_pool().fetch(  # type: ignore[union-attr]
            """SELECT id, conversation_id, role, content, tool_calls, tool_call_id, name, created_at
               FROM messages WHERE conversation_id = $1 ORDER BY created_at ASC""",
            uuid.UUID(conversation_id),
        )
        return [_row_to_message(r) for r in rows]
    return list(_mem_messages.get(conversation_id, []))


def _row_to_conversation(r) -> Conversation:
    return Conversation(
        id=str(r["id"]),
        title=r["title"],
        projectPath=r["project_path"],
        createdAt=r["created_at"].isoformat(),
        updatedAt=r["updated_at"].isoformat(),
    )


def _row_to_message(r) -> ChatMessage:
    raw_tool_calls = r["tool_calls"]
    tool_calls = None
    if raw_tool_calls:
        data = raw_tool_calls if isinstance(raw_tool_calls, list) else json.loads(raw_tool_calls)
        tool_calls = [ToolCallRecord(**tc) for tc in data]
    return ChatMessage(
        id=str(r["id"]),
        conversationId=str(r["conversation_id"]),
        role=r["role"],
        content=r["content"],
        toolCalls=tool_calls,
        toolCallId=r["tool_call_id"],
        name=r["name"],
        createdAt=r["created_at"].isoformat(),
    )
