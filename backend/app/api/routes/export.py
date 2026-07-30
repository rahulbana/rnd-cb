"""Export an article to PDF / DOCX / Markdown."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.article import Article
from app.models.user import User
from app.services.export import EXPORTERS

router = APIRouter(prefix="/articles", tags=["export"])


def _safe_filename(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (title or "article").strip()).strip("-")
    return (slug or "article").lower()[:60]


@router.get("/{article_id}/export")
async def export_article(
    article_id: str,
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fmt = format.lower()
    if fmt not in EXPORTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Use one of: pdf, docx, md.",
        )

    article = await db.get(Article, article_id)
    if article is None or article.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    exporter, media_type, ext = EXPORTERS[fmt]
    data = exporter(article)
    filename = f"{_safe_filename(article.title)}.{ext}"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
