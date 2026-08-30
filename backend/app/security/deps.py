"""FastAPI security dependencies.

Authentication is optional: anonymous callers get ``user_id = None`` (their
trips are shared/local), while a valid bearer token scopes data to that user.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..models.db import get_session
from ..repositories import user_repository
from .auth import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_optional_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    if creds is None:
        return None
    payload = decode_token(creds.credentials)
    if not payload:
        return None
    return payload.get("sub")


def require_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = user_repository.get(session, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user.id
