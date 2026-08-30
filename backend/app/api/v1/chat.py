"""AI travel-assistant chat endpoints (spec section 15)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...models.db import get_session
from ...schemas.chat import ChatRequest, ChatResponse, StreamEvent
from ...security import get_optional_user_id
from ...services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, session: Session = Depends(get_session),
               user_id: str | None = Depends(get_optional_user_id)) -> ChatResponse:
    return await chat_service.handle_chat(session, payload, user_id)


@router.post("/stream")
async def chat_stream(payload: ChatRequest, session: Session = Depends(get_session),
                      user_id: str | None = Depends(get_optional_user_id)) -> StreamingResponse:
    async def gen():
        yield f"data: {StreamEvent(type='status', message='Thinking…').model_dump_json()}\n\n"
        response = await chat_service.handle_chat(session, payload, user_id)
        # Stream the reply word-by-word for a responsive feel.
        for word in response.reply.split(" "):
            yield f"data: {StreamEvent(type='token', message=word + ' ').model_dump_json()}\n\n"
            await asyncio.sleep(0)
        yield f"data: {StreamEvent(type='result', data=response.model_dump()).model_dump_json()}\n\n"
        yield f"data: {StreamEvent(type='done').model_dump_json()}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
