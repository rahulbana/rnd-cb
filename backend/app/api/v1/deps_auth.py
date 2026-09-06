"""Authentication dependencies: current user (JWT or API key) and RBAC."""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import TOKEN_TYPE_ACCESS, decode_token, hash_api_key
from app.db.base import get_db
from app.db.models import ApiKey, User

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=401,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _user_from_jwt(token: str, db: Session) -> User | None:
    try:
        payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    except jwt.PyJWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.get(User, user_id)


def _user_from_api_key(raw_key: str, db: Session) -> User | None:
    row = db.execute(
        select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key))
    ).scalar_one_or_none()
    if row is None:
        return None
    row.last_used_at = datetime.now(UTC)
    db.commit()
    return db.get(User, row.user_id)


def get_current_user(
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer),
    api_key: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller from a JWT access token or an API key."""
    user: User | None = None
    if bearer is not None:
        user = _user_from_jwt(bearer.credentials, db)
    if user is None and api_key:
        user = _user_from_api_key(api_key, db)
    if user is None:
        raise _UNAUTHORIZED
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
