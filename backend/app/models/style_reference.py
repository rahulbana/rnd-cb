"""Writing-style reference material uploaded by a user.

These are links or documents of the user's previous writing, used as
style/voice context for the LLM during generation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StyleReference(Base):
    __tablename__ = "style_references"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(512), default="Untitled")
    source_type: Mapped[str] = mapped_column(String(16), default="file")  # file | link
    origin: Mapped[str] = mapped_column(String(1024), default="")  # url or filename
    content: Mapped[str] = mapped_column(Text, default="")
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="style_references")  # noqa: F821
