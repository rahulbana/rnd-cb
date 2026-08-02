"""Bootstrap the initial superadmin account on first startup."""
from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User
from app.services import get_user_by_email

logger = logging.getLogger("app.seed")


async def ensure_superadmin() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        existing = await get_user_by_email(db, settings.first_superadmin_email)
        if existing is not None:
            return
        db.add(
            User(
                email=settings.first_superadmin_email,
                full_name=settings.first_superadmin_name,
                hashed_password=hash_password(settings.first_superadmin_password),
                is_superadmin=True,
                is_active=True,
            )
        )
        await db.commit()
        logger.info(
            "Created bootstrap superadmin '%s'", settings.first_superadmin_email
        )
