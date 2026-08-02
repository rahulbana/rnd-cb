from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dashboard import Dashboard
    from app.models.user import User


class DashboardAccess(Base):
    """Grants a user ``developer`` or ``viewer`` access to a single dashboard."""

    __tablename__ = "dashboard_access"
    __table_args__ = (
        UniqueConstraint("user_id", "dashboard_id", name="uq_access_user_dashboard"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="dashboard_access")
    dashboard: Mapped["Dashboard"] = relationship(back_populates="access_grants")
