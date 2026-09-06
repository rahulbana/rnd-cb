"""Security primitives: Argon2 password hashing, JWT, API keys.

Phase 8 makes these real: Argon2id for passwords, JWT access + refresh tokens
with a type claim, and SHA-256-hashed API keys for service-to-service auth.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

API_KEY_PREFIX = "rag_"


# --- Passwords (Argon2id) --------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _hasher.verify(encoded, password)
    except (VerifyMismatchError, Exception):  # noqa: BLE001 - any failure = invalid
        return False


def needs_rehash(encoded: str) -> bool:
    try:
        return _hasher.check_needs_rehash(encoded)
    except Exception:  # noqa: BLE001
        return False


# --- API keys --------------------------------------------------------------


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, key_hash). The raw key is shown to the user once."""
    raw = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return raw, hash_api_key(raw)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# --- JWT -------------------------------------------------------------------


def _create_token(
    subject: str, *, token_type: str, expires: timedelta, claims: dict[str, Any]
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        **claims,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str, *, org_id: str, role: str, extra_claims: dict[str, Any] | None = None
) -> str:
    claims = {"org_id": org_id, "role": role, **(extra_claims or {})}
    return _create_token(
        subject,
        token_type=TOKEN_TYPE_ACCESS,
        expires=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        claims=claims,
    )


def create_refresh_token(subject: str, *, org_id: str) -> str:
    return _create_token(
        subject,
        token_type=TOKEN_TYPE_REFRESH,
        expires=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        claims={"org_id": org_id},
    )


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and verify a JWT; optionally enforce its ``type`` claim."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if expected_type is not None and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"expected {expected_type} token, got {payload.get('type')}"
        )
    return payload
