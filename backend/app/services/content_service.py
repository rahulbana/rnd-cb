"""Persistence helpers for generated content."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentPiece
from app.schemas import GenerateRequest


async def save_content(db: AsyncSession, req: GenerateRequest, result: dict) -> ContentPiece:
    piece = ContentPiece(
        topic=req.topic,
        platform=req.platform.value,
        tone=req.tone.value,
        length=req.length.value,
        audience=req.audience,
        preferences=req.preferences,
        title=result.get("title", ""),
        body=result.get("body", ""),
        description=result.get("description", ""),
        keywords=result.get("keywords", []),
        hashtags=result.get("hashtags", []),
        trending_topic=result.get("trending_topic", ""),
        sources=result.get("sources", []),
        verification=result.get("verification", {}),
        status="completed",
    )
    db.add(piece)
    await db.commit()
    await db.refresh(piece)
    return piece


async def list_content(db: AsyncSession, limit: int = 50) -> list[ContentPiece]:
    result = await db.execute(select(ContentPiece).order_by(ContentPiece.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_content(db: AsyncSession, content_id: str) -> ContentPiece | None:
    result = await db.execute(select(ContentPiece).where(ContentPiece.id == content_id))
    return result.scalar_one_or_none()
