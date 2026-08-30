"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ...models.db import get_session
from ...repositories import user_repository
from ...security import create_access_token, hash_password, require_user_id, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    preferences: dict = {}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    if user_repository.get_by_email(session, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = user_repository.create(
        session, email=payload.email, hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = user_repository.get_by_email(session, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user_id: str = Depends(require_user_id), session: Session = Depends(get_session)) -> UserOut:
    user = user_repository.get(session, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserOut(id=user.id, email=user.email, full_name=user.full_name,
                   preferences=user.preferences or {})


class PreferencesUpdate(BaseModel):
    preferences: dict


@router.patch("/me/preferences", response_model=UserOut)
def update_preferences(payload: PreferencesUpdate, user_id: str = Depends(require_user_id),
                       session: Session = Depends(get_session)) -> UserOut:
    user = user_repository.update_preferences(session, user_id, payload.preferences)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserOut(id=user.id, email=user.email, full_name=user.full_name,
                   preferences=user.preferences or {})
