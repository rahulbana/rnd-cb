import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..llm import chat_completion, get_langfuse
from ..memory import (
    extract_and_store_memories,
    get_short_term_messages,
    retrieve_long_term,
)
from ..models import ChatSession, Memory, Message, User, utcnow
from ..schemas import (
    ChatRequest,
    ChatResponse,
    MemoryOut,
    MessageOut,
    SessionDetail,
    SessionOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

SYSTEM_PROMPT = (
    "You are a helpful, friendly assistant with memory. "
    "Use the conversation history (short-term memory) and the known facts "
    "about the user (long-term memory) to give personalized, coherent "
    "answers. Do not invent facts about the user that you were not told."
)


def _get_owned_session(db: Session, user: User, session_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(db.scalars(stmt))


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    session = ChatSession(user_id=user.id, title="New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _get_owned_session(db, user, session_id)
    return SessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[MessageOut.model_validate(m) for m in session.messages],
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _get_owned_session(db, user, session_id)
    db.delete(session)
    db.commit()


@router.get("/memories", response_model=list[MemoryOut])
def list_memories(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    stmt = (
        select(Memory)
        .where(Memory.user_id == user.id)
        .order_by(Memory.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Resolve or create the session.
    if payload.session_id is not None:
        session = _get_owned_session(db, user, payload.session_id)
    else:
        session = ChatSession(user_id=user.id, title=payload.message[:50])
        db.add(session)
        db.commit()
        db.refresh(session)

    # ---- Langfuse trace: one per request, tied to user + session ----
    langfuse = get_langfuse()
    trace = None
    trace_id = None
    if langfuse is not None:
        try:
            trace = langfuse.trace(
                name="chat-request",
                user_id=str(user.id),
                session_id=str(session.id),
                input=payload.message,
                metadata={"username": user.username},
                tags=["chatbot"],
            )
            trace_id = trace.id
        except Exception as exc:  # pragma: no cover
            logger.debug("Langfuse trace start failed: %s", exc)

    # Persist the user's message (part of short-term memory).
    db.add(Message(session_id=session.id, role="user", content=payload.message))
    db.commit()

    # ---- Build the prompt from memory ----
    long_term = retrieve_long_term(db, user.id, payload.message, trace=trace)
    short_term = get_short_term_messages(db, session.id)

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if long_term:
        facts = "\n".join(f"- {f}" for f in long_term)
        messages.append(
            {
                "role": "system",
                "content": f"Known facts about the user (long-term memory):\n{facts}",
            }
        )
    messages.extend(short_term)

    # ---- Generate the reply ----
    try:
        reply = chat_completion(messages, trace=trace, generation_name="assistant")
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM request failed: {exc}",
        )

    # Persist the assistant reply and touch the session's updated_at.
    db.add(Message(session_id=session.id, role="assistant", content=reply))
    session.updated_at = utcnow()
    db.commit()

    # ---- Update long-term memory from this exchange ----
    extract_and_store_memories(
        db, user.id, payload.message, reply, trace=trace
    )

    if trace is not None:
        try:
            trace.update(output=reply)
            langfuse.flush()
        except Exception as exc:  # pragma: no cover
            logger.debug("Langfuse flush failed: %s", exc)

    return ChatResponse(session_id=session.id, reply=reply, trace_id=trace_id)
