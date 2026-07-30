"""AI content generation route.

Pipeline: RAG style context → optional deep web research → LLM generation
→ duplicate detection. Sources are merged and deduped across all stages.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.article import Article
from app.models.style_reference import StyleReference
from app.models.user import User
from app.schemas.generation import (
    DuplicateHit,
    ExpandRequest,
    ExpandResponse,
    GenerationRequest,
    GenerationResponse,
    Source,
)
from app.services.llm import expand_content, generate_content
from app.services.research import deep_research
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/generate", tags=["generation"])


async def _fetch_articles(db: AsyncSession, ids: list[str]) -> dict[str, Article]:
    out: dict[str, Article] = {}
    for aid in ids:
        art = await db.get(Article, aid)
        if art is not None:
            out[aid] = art
    return out


async def _fetch_style_refs(
    db: AsyncSession, ids: list[str]
) -> dict[str, StyleReference]:
    out: dict[str, StyleReference] = {}
    for rid in ids:
        ref = await db.get(StyleReference, rid)
        if ref is not None:
            out[rid] = ref
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
    internal_sources: list[Source] = []
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
                internal_sources.append(
                    Source(
                        title=art.title or "Untitled",
                        url=f"/articles/{aid}",
                        type="internal",
                        snippet="Your previous article used as style/context reference.",
                    )
                )

    # --- 1b. Writing-style references the user uploaded in Settings ---
    style_hits = await asyncio.to_thread(
        store.search_style_references, query=req.prompt, user_id=user.id, n_results=2
    )
    if style_hits:
        refs = await _fetch_style_refs(db, [h[0] for h in style_hits])
        style_samples = [
            f"Sample — {refs[rid].name}:\n{refs[rid].content[:1500]}"
            for rid, _ in style_hits
            if rid in refs and refs[rid].content
        ]
        if style_samples:
            rag_context.append(
                "The following are samples of the author's own previous "
                "writing. Study and closely match their voice, tone, sentence "
                "rhythm and vocabulary (do not copy content):\n"
                + "\n\n".join(style_samples)
            )

    # --- 2. Deep web research (optional): ground the article in real sources ---
    web_findings = ""
    web_sources: list[Source] = []
    research_queries: list[str] = []
    if req.use_web_search:
        research = await asyncio.to_thread(deep_research, req.prompt, req.research_depth)
        web_findings = research.findings
        web_sources = research.sources
        research_queries = research.queries

    # --- 3. Generate content via the LLM ---
    content = await asyncio.to_thread(
        generate_content, req, rag_context, web_findings or None
    )

    # Merge sources: verifiable internal (writer's own) + researched web
    # sources first, then any additional references the model cited, deduped.
    merged: list[Source] = []
    seen: set[str] = set()
    for s in internal_sources + web_sources + content.sources:
        key = (s.url or s.title or "").lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(s)
    content.sources = merged

    # --- 4. Duplicate detection against existing library ---
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
        research_queries=research_queries,
    )


@router.post("/expand", response_model=ExpandResponse)
async def expand(
    req: ExpandRequest,
    user: User = Depends(get_current_user),
):
    """Expand/lengthen an existing article body."""
    body = await asyncio.to_thread(
        expand_content,
        title=req.title,
        body=req.body,
        mode=req.mode,
        instruction=req.instruction,
    )
    return ExpandResponse(body=body)
