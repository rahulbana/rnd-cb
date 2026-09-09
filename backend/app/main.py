"""FastAPI application: routes, streaming chat, error handling."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import require_auth
from .config import get_settings
from .conversation import ConversationManager
from .database import engine, get_db, init_db
from .llm import LLMError, get_llm_client, model_supports_temperature
from .logging_config import configure_logging, get_logger
from .schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    UserInfo,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: initializing database (%s)", settings.database_url)
    await init_db()
    logger.info("Using model: %s (effort=%s)", settings.model, settings.effort)
    yield
    logger.info("Shutting down.")
    await engine.dispose()


app = FastAPI(title="Production AI Chatbot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Meta ------------------------------------------------------------------
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me", response_model=UserInfo)
async def me(username: str = Depends(require_auth)) -> UserInfo:
    """Verify credentials and report active model / capabilities."""
    return UserInfo(
        username=username,
        model=settings.model,
        temperature_supported=model_supports_temperature(settings.model),
    )


# --- Conversations ---------------------------------------------------------
@app.get("/api/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSummary]:
    manager = ConversationManager(db)
    return await manager.list_conversations()


@app.post(
    "/api/conversations",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    manager = ConversationManager(db)
    conversation = await manager.create_conversation(
        title=payload.title,
        system_prompt=payload.system_prompt,
        temperature=payload.temperature,
    )
    return await manager.get_conversation(conversation.id, with_messages=True)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    manager = ConversationManager(db)
    conversation = await manager.get_conversation(
        conversation_id, with_messages=True
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    manager = ConversationManager(db)
    conversation = await manager.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await manager.update_conversation(
        conversation,
        title=payload.title,
        system_prompt=payload.system_prompt,
        temperature=payload.temperature,
    )
    return await manager.get_conversation(conversation_id, with_messages=True)


@app.delete(
    "/api/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_conversation(
    conversation_id: str,
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    manager = ConversationManager(db)
    deleted = await manager.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Chat (streaming) ------------------------------------------------------
def _sse(payload: dict) -> str:
    """Format a payload as a Server-Sent Events data frame."""
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    payload: ChatRequest,
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Persist the user message and stream the assistant reply via SSE.

    The response is a text/event-stream. Each frame is JSON with a ``type``:
      - ``delta``: incremental assistant text (``text`` field)
      - ``done``:  stream finished (``message_id`` field)
      - ``error``: an error occurred mid-stream (``detail`` field)
    """
    manager = ConversationManager(db)
    conversation = await manager.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Persist the user's message first.
    await manager.add_message(conversation_id, role="user", content=payload.content)

    system_prompt = conversation.system_prompt
    temperature = conversation.temperature
    history = await manager.get_history_for_llm(conversation_id)
    llm = get_llm_client()

    async def event_stream() -> AsyncGenerator[str, None]:
        parts: list[str] = []
        try:
            async for chunk in llm.stream_chat(
                messages=history,
                system_prompt=system_prompt,
                temperature=temperature,
            ):
                parts.append(chunk)
                yield _sse({"type": "delta", "text": chunk})
        except LLMError as exc:
            logger.error("LLM error during stream: %s", exc.message)
            # Save any partial content so the conversation is not lost.
            if parts:
                await manager.add_message(
                    conversation_id, role="assistant", content="".join(parts)
                )
            yield _sse({"type": "error", "detail": exc.message})
            return
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors
            logger.exception("Unexpected error during stream")
            yield _sse(
                {"type": "error", "detail": "An unexpected error occurred."}
            )
            return

        full_text = "".join(parts)
        message = await manager.add_message(
            conversation_id, role="assistant", content=full_text
        )
        yield _sse({"type": "done", "message_id": message.id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
