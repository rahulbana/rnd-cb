"""Semantic search over the writer's article library."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.article import Article
from app.models.user import User
from app.schemas.article import ArticleListItem, SearchResult
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    store = get_vector_store()
    hits = await asyncio.to_thread(
        store.search, query=q, user_id=user.id, n_results=limit
    )
    results: list[SearchResult] = []
    for aid, distance in hits:
        article = await db.get(Article, aid)
        if article is None or article.user_id != user.id:
            continue
        results.append(
            SearchResult(
                article=ArticleListItem.model_validate(article),
                score=round(max(0.0, 1.0 - distance), 4),
            )
        )
    return results
