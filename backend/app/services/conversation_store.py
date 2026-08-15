"""CRUD for conversations, kept separate from the HTTP layer.

On upsert the message set is replaced wholesale (delete + re-insert in order).
Conversations are small, so this is simpler and correct versus diffing, and the
frontend already persists the full message array per turn.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import Conversation, Message, now_ms


def list_conversations(db: Session) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    return list(db.scalars(stmt).all())


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def upsert_conversation(
    db: Session, conversation_id: str, title: str | None, messages: list[dict]
) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        conv = Conversation(id=conversation_id, title=title or "New chat", created_at=now_ms())
        db.add(conv)
    if title is not None:
        conv.title = title
    conv.updated_at = now_ms()

    # Replace messages.
    db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    for i, m in enumerate(messages or []):
        db.add(Message(
            conversation_id=conversation_id,
            position=i,
            role=m.get("role", "assistant"),
            content=m.get("text", "") or "",
            status=m.get("status"),
            sources=m.get("sources"),
            steps=m.get("steps"),
        ))
    db.commit()
    db.refresh(conv)
    return conv


def rename_conversation(db: Session, conversation_id: str, title: str) -> Conversation | None:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return None
    conv.title = title
    conv.updated_at = now_ms()
    db.commit()
    db.refresh(conv)
    return conv


def delete_conversation(db: Session, conversation_id: str) -> bool:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return False
    db.delete(conv)
    db.commit()
    return True
