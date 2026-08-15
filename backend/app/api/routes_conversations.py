"""Conversation history endpoints (SQLite/Postgres-backed)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.models import Conversation
from ..db.session import get_db
from ..services import conversation_store as store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---- schemas ----
class MessageIn(BaseModel):
    role: str
    text: str = ""
    status: str | None = None
    sources: list | None = None
    steps: list | None = None


class ConversationUpsert(BaseModel):
    title: str | None = None
    messages: list[MessageIn] = []


class RenameIn(BaseModel):
    title: str


def _summary(conv: Conversation) -> dict:
    return {
        "id": conv.id,
        "title": conv.title,
        "createdAt": conv.created_at,
        "updatedAt": conv.updated_at,
        "messageCount": len(conv.messages),
    }


def _full(conv: Conversation) -> dict:
    return {
        **_summary(conv),
        "messages": [
            {
                "role": m.role,
                "text": m.content,
                "status": m.status,
                "sources": m.sources or [],
                "steps": m.steps or [],
            }
            for m in conv.messages
        ],
    }


@router.get("")
def list_conversations(db: Session = Depends(get_db)) -> dict:
    return {"conversations": [_summary(c) for c in store.list_conversations(db)]}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    conv = store.get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _full(conv)


@router.put("/{conversation_id}")
def upsert_conversation(
    conversation_id: str, body: ConversationUpsert, db: Session = Depends(get_db)
) -> dict:
    conv = store.upsert_conversation(
        db, conversation_id, body.title, [m.model_dump() for m in body.messages]
    )
    return _summary(conv)


@router.patch("/{conversation_id}")
def rename_conversation(
    conversation_id: str, body: RenameIn, db: Session = Depends(get_db)
) -> dict:
    conv = store.rename_conversation(db, conversation_id, body.title)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _summary(conv)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    ok = store.delete_conversation(db, conversation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": conversation_id}
