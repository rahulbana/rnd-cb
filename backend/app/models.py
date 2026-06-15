"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ContentPiece(Base):
    """A generated piece of content along with its research provenance."""

    __tablename__ = "content_pieces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Request parameters
    topic: Mapped[str] = mapped_column(String(500), default="")
    platform: Mapped[str] = mapped_column(String(50), default="linkedin")
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    length: Mapped[str] = mapped_column(String(50), default="medium")
    audience: Mapped[str] = mapped_column(String(255), default="")
    preferences: Mapped[str] = mapped_column(Text, default="")

    # Generated content
    title: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    hashtags: Mapped[list] = mapped_column(JSON, default=list)

    # Research provenance
    trending_topic: Mapped[str] = mapped_column(String(500), default="")
    sources: Mapped[list] = mapped_column(JSON, default=list)
    verification: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(30), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "platform": self.platform,
            "tone": self.tone,
            "length": self.length,
            "audience": self.audience,
            "preferences": self.preferences,
            "title": self.title,
            "body": self.body,
            "description": self.description,
            "keywords": self.keywords or [],
            "hashtags": self.hashtags or [],
            "trending_topic": self.trending_topic,
            "sources": self.sources or [],
            "verification": self.verification or {},
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
