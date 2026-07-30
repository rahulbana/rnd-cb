"""Article ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # The writer's original brief / request that produced this article.
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Core content
    title: Mapped[str] = mapped_column(String(512), default="Untitled")
    body: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")

    # SEO
    seo_description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    # NLP metadata
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    ner_tags: Mapped[list] = mapped_column(JSON, default=list)

    # Resources/references the content was drawn from.
    sources: Mapped[list] = mapped_column(JSON, default=list)

    # Banner image (relative media URL, e.g. /media/banners/<uuid>.png)
    banner_image: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Observability: the Langfuse trace that produced this article, plus the
    # original AI-generated body (used to score how much the user edited it).
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generated_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|published

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="articles")  # noqa: F821
