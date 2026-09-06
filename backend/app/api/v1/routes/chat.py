"""Chat routes: grounded generation (sync + SSE streaming) and history."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps_auth import get_current_user
from app.api.v1.schemas import (
    ChatRequest,
    ChatResponse,
    CitationOut,
    ConversationOut,
    MessageOut,
)
from app.core.config import settings
from app.core.registry import (
    get_llm_provider,
    get_reranker,
    get_retriever,
    get_tracer,
)
from app.db.base import get_db
from app.db.models import Conversation, Message, User
from app.domain.models import Citation
from app.services.chat_service import ChatService
from app.services.context_assembly import ContextAssembler
from app.services.conversation_memory import ConversationMemory
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["chat"])


def _build_chat_service(db: Session, user: User) -> ChatService:
    llm = get_llm_provider()
    retrieval = RetrievalService(get_retriever(), db)
    memory = ConversationMemory(
        db,
        llm,
        window=settings.CHAT_HISTORY_WINDOW,
        summarize=settings.CHAT_SUMMARIZE,
    )
    assembler = ContextAssembler(
        token_budget=settings.CONTEXT_TOKEN_BUDGET,
        mmr_lambda=settings.MMR_LAMBDA,
        dedup_threshold=settings.DEDUP_JACCARD,
        count_tokens=llm.count_tokens,  # provider-specific tokenizer
    )
    return ChatService(
        llm,
        retrieval,
        get_reranker(),
        memory,
        assembler=assembler,
        temperature=settings.LLM_TEMPERATURE,
        top_k=settings.RETRIEVE_TOP_K,
        fetch_k=settings.RERANK_FETCH_K,
        not_found_message=settings.NOT_FOUND_MESSAGE,
        user_id=user.id,
        tracer=get_tracer(),
    )


def _citation_out(c: Citation) -> CitationOut:
    return CitationOut(
        chunk_id=c.chunk_id,
        document_id=c.document_id,
        page=c.page,
        heading_path=c.heading_path,
        score=c.score,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    """Answer a question, grounded in the org's documents, with citations."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")
    service = _build_chat_service(db, user)
    result = await service.answer(
        request.question,
        namespace=user.org_id,
        conversation_id=request.conversation_id,
    )
    return ChatResponse(
        conversation_id=result.conversation_id,
        answer=result.answer,
        citations=[_citation_out(c) for c in result.citations],
        provider=result.provider,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        latency_ms=result.latency_ms,
        cost_usd=result.cost_usd,
        prompt_version=result.prompt_version,
        found=result.found,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a grounded answer over SSE, followed by its citations."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")
    service = _build_chat_service(db, user)
    handle = await service.stream(
        request.question,
        namespace=user.org_id,
        conversation_id=request.conversation_id,
    )

    async def _events() -> AsyncIterator[str]:
        meta = {
            "conversation_id": handle.conversation_id,
            "found": handle.found,
            "citations": [_citation_out(c).model_dump() for c in handle.citations],
        }
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
        async for token in handle.tokens:
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream")


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ConversationOut]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return [
        ConversationOut(id=c.id, title=c.title) for c in db.execute(stmt).scalars().all()
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageOut]:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )
    out: list[MessageOut] = []
    for m in db.execute(stmt).scalars().all():
        citations = ConversationMemory.serialize_citations(m.citations)
        out.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                provider=m.provider,
                citations=[CitationOut(**c) for c in citations],
                tokens_in=m.tokens_in,
                tokens_out=m.tokens_out,
                latency_ms=m.latency_ms,
            )
        )
    return out
