"""Article CRUD routes."""
from __future__ import annotations

import asyncio
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session_id
from app.core.database import get_db
from app.models.article import Article
from app.models.user import User
from app.schemas.article import (
    ArticleCreate,
    ArticleListItem,
    ArticleOut,
    ArticleUpdate,
)
from app.services import observability as obs
from app.services.images import generate_banner
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/articles", tags=["articles"])


async def _index_article(article: Article) -> None:
    store = get_vector_store()
    await asyncio.to_thread(
        store.upsert_article,
        article_id=article.id,
        user_id=article.user_id,
        title=article.title,
        body=article.body,
        summary=article.summary,
    )


async def _get_owned_article(db: AsyncSession, article_id: str, user: User) -> Article:
    article = await db.get(Article, article_id)
    if article is None or article.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


@router.get("", response_model=list[ArticleListItem])
async def list_articles(
    q: str | None = Query(default=None, description="Filter by title substring"),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Article).where(Article.user_id == user.id)
    if q:
        stmt = stmt.where(Article.title.ilike(f"%{q}%"))
    if status_filter:
        stmt = stmt.where(Article.status == status_filter)
    stmt = stmt.order_by(Article.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article(
    payload: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    article = Article(user_id=user.id, **data)
    # Snapshot the AI-generated body so we can later score how much the user
    # edits it (only meaningful for articles created from a generation).
    if article.trace_id:
        article.generated_body = article.body
    db.add(article)
    await db.commit()
    await db.refresh(article)
    await _index_article(article)
    return article


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_owned_article(db, article_id, user)


@router.patch("/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: str,
    payload: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    article = await _get_owned_article(db, article_id, user)
    # model_dump recursively converts nested models (ner_tags, sources) to dicts.
    updates = payload.model_dump(exclude_unset=True)
    body_changed = "body" in updates and updates["body"] != article.body
    for field, value in updates.items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    await _index_article(article)

    # Edit-retention quality signal: how close the saved body still is to the
    # original AI generation (1.0 = untouched, lower = heavily rewritten).
    if body_changed and article.trace_id and article.generated_body:
        retention = round(
            SequenceMatcher(None, article.generated_body, article.body or "").ratio(), 4
        )
        await asyncio.to_thread(
            obs.score,
            trace_id=article.trace_id,
            name="edit_retention",
            value=retention,
            data_type="NUMERIC",
            comment="Similarity of saved article to the AI-generated draft",
        )
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    article = await _get_owned_article(db, article_id, user)
    await db.delete(article)
    await db.commit()
    await asyncio.to_thread(get_vector_store().delete_article, article_id)


@router.post("/{article_id}/banner", response_model=ArticleOut)
async def generate_article_banner(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    session_id: str | None = Depends(get_session_id),
):
    """Generate (or regenerate) a title-aware banner image for the article."""
    article = await _get_owned_article(db, article_id, user)
    with obs.span("image.banner", input={"title": article.title}) as trace:
        banner_url = await asyncio.to_thread(
            generate_banner,
            title=article.title,
            summary=article.summary,
            tags=article.tags or [],
        )
        obs.set_trace(
            user_id=user.id,
            session_id=session_id,
            tags=["banner_image"],
            output={"url": banner_url},
        )
        trace.update(output={"url": banner_url})
    article.banner_image = banner_url
    await db.commit()
    await db.refresh(article)
    return article
