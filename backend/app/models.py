"""SQLAlchemy ORM models.

The generated plan is stored denormalized as JSON blobs alongside a few queryable
columns. For this app the plan is always read/written as a whole document, so a
document-style row is simpler and cheaper than a fully normalized schema, while
the promoted columns (goal, diet_type, target_kcal, approved) keep list/filter
queries index-friendly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Promoted, queryable columns.
    goal: Mapped[str] = mapped_column(String(32), nullable=False)
    diet_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Full documents (validated Pydantic models dumped to dict).
    intake: Mapped[dict] = mapped_column(JSON, nullable=False)
    nutrition: Mapped[dict] = mapped_column(JSON, nullable=False)
    meal_plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    safety: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
