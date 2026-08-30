"""User repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.tables import User


class UserRepository:
    def get_by_email(self, session: Session, email: str) -> User | None:
        return session.scalar(select(User).where(User.email == email.lower()))

    def get(self, session: Session, user_id: str) -> User | None:
        return session.get(User, user_id)

    def create(self, session: Session, *, email: str, hashed_password: str,
               full_name: str | None = None) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password, full_name=full_name)
        session.add(user)
        session.flush()
        return user

    def update_preferences(self, session: Session, user_id: str, preferences: dict) -> User | None:
        user = session.get(User, user_id)
        if user is None:
            return None
        user.preferences = preferences
        session.flush()
        return user


user_repository = UserRepository()
