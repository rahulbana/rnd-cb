"""Auth routes: register, login, refresh, me, and API keys."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps_auth import get_current_user
from app.api.v1.schemas import (
    AccessTokenResponse,
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyOut,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.core.ratelimit import RateLimiter, get_auth_rate_limiter
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    decode_token,
)
from app.db.base import get_db
from app.db.models import User
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role, org_id=user.org_id)


def _tokens(service: AuthService, user: User) -> TokenResponse:
    pair = service.tokens(user)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        user=_user_out(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    try:
        user = service.register(str(body.email), body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _tokens(service, user)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    limiter: RateLimiter = Depends(get_auth_rate_limiter),
) -> TokenResponse:
    if not limiter.allow():
        raise HTTPException(status_code=429, detail="Too many login attempts")
    service = AuthService(db)
    try:
        user = service.authenticate(str(body.email), body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _tokens(service, user)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    body: RefreshRequest, db: Session = Depends(get_db)
) -> AccessTokenResponse:
    try:
        payload = decode_token(body.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    token = create_access_token(user.id, org_id=user.org_id, role=user.role)
    return AccessTokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: ApiKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreatedResponse:
    raw, api_key = AuthService(db).create_api_key(user, body.scopes)
    return ApiKeyCreatedResponse(
        id=api_key.id, scopes=api_key.scopes, api_key=raw, last_used_at=None
    )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ApiKeyOut]:
    return [
        ApiKeyOut(
            id=k.id,
            scopes=k.scopes,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in AuthService(db).list_api_keys(user)
    ]
