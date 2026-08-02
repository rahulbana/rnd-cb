"""Small reusable service-layer helpers shared across routes."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def resolve_or_create_user(
    db: AsyncSession,
    *,
    email: str,
    full_name: str | None,
    password: str | None,
) -> User:
    """Return the existing user with ``email`` or create a new one.

    When creating, both ``full_name`` and ``password`` are required.
    """
    existing = await get_user_by_email(db, email)
    if existing is not None:
        return existing

    if not full_name or not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No user with that email exists. Provide full_name and "
                "password to create a new user."
            ),
        )

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        is_superadmin=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user
