"""AI content generation route (with RAG context + duplicate detection)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.article import Article
from app.models.user import User
from app.schemas.generation import (
    DuplicateHit,
    GenerationRequest,
    GenerationResponse,
)
from app.services.llm import generate_content
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/generate", tags=["generation"])


async def _fetch_articles(db: AsyncSession, ids: list[str]) -> dict[str, Article]:
    out: dict[str, Article] = {}
    for aid in ids:
        art = await db.get(Article, aid)
        if art is not None:
            out[aid] = art
    return out


@router.post("", response_model=GenerationResponse)
async def generate(
    req: GenerationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    store = get_vector_store()

    # --- 1. RAG: gather style context from the writer's past articles ---
    rag_context: list[str] = []
    context_ids: list[str] = []
    if req.use_rag:
        hits = await asyncio.to_thread(
            store.search, query=req.prompt, user_id=user.id, n_results=3
        )
        articles = await _fetch_articles(db, [h[0] for h in hits])
        for aid, _dist in hits:
            art = articles.get(aid)
            if art and art.body:
                context_ids.append(aid)
                rag_context.append(f"Title: {art.title}\n{art.body[:1200]}")

    # --- 2. Generate content via the LLM ---
    content = await asyncio.to_thread(generate_content, req, rag_context)

    # --- 3. Duplicate detection against existing library ---
    dup_hits = await asyncio.to_thread(
        store.find_similar,
        title=content.title,
        body=content.body,
        summary=content.summary,
        user_id=user.id,
        n_results=5,
    )
    dup_ids = [aid for aid, dist in dup_hits if dist <= settings.DUPLICATE_DISTANCE_THRESHOLD]
    dup_articles = await _fetch_articles(db, dup_ids)
    possible_duplicates = [
        DuplicateHit(
            article_id=aid,
            title=dup_articles[aid].title if aid in dup_articles else "Unknown",
            distance=round(dist, 4),
        )
        for aid, dist in dup_hits
        if dist <= settings.DUPLICATE_DISTANCE_THRESHOLD and aid in dup_articles
    ]

    return GenerationResponse(
        content=content,
        context_used=context_ids,
        possible_duplicates=possible_duplicates,
    )
