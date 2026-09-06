"""Authentication & account service.

Single-org today: every user is created in the default org. The first user
becomes admin (bootstrap); everyone else is a regular user. Passwords are
Argon2id; API keys are stored only as SHA-256 hashes.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from app.db.models import ApiKey, User


class AuthError(Exception):
    """Raised for auth failures the API maps to 401/409."""

    def __init__(self, message: str, *, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def register(self, email: str, password: str) -> User:
        email = email.strip().lower()
        if not email or not password:
            raise AuthError("Email and password are required", status_code=400)
        existing = self._db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            raise AuthError("Email already registered", status_code=409)

        count = self._db.execute(select(func.count()).select_from(User)).scalar_one()
        role = "admin" if count == 0 and settings.FIRST_USER_IS_ADMIN else "user"

        user = User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            org_id=settings.DEFAULT_ORG_ID,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self._db.execute(
            select(User).where(User.email == email.strip().lower())
        ).scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        return user

    def tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id, org_id=user.org_id, role=user.role),
            refresh_token=create_refresh_token(user.id, org_id=user.org_id),
        )

    def get_user(self, user_id: str) -> User | None:
        return self._db.get(User, user_id)

    def create_api_key(self, user: User, scopes: str = "") -> tuple[str, ApiKey]:
        raw, key_hash = generate_api_key()
        api_key = ApiKey(user_id=user.id, key_hash=key_hash, scopes=scopes)
        self._db.add(api_key)
        self._db.commit()
        self._db.refresh(api_key)
        return raw, api_key

    def list_api_keys(self, user: User) -> list[ApiKey]:
        return list(
            self._db.execute(select(ApiKey).where(ApiKey.user_id == user.id))
            .scalars()
            .all()
        )
