"""Security primitives: password hashing, JWT, API-key hashing.

Phase 1 provides the primitives and shapes; full auth flows (register/login/
refresh, RBAC, rate limiting) land in Phase 8. Kept dependency-light so the
skeleton boots without optional crypto libraries.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings


def hash_password(password: str, *, salt: str | None = None) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256.

    Phase 8 replaces this with Argon2; the interface (``hash_password`` /
    ``verify_password``) stays the same so callers do not change.
    """
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    )
    return f"pbkdf2_sha256$100000${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verify against a ``hash_password`` output."""
    try:
        algo, iters, salt, _ = encoded.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    expected = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters)
    ).hex()
    return hmac.compare_digest(expected, encoded.split("$")[-1])


def hash_api_key(raw_key: str) -> str:
    """Deterministic SHA-256 hash for API-key storage/lookup."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str, *, extra_claims: dict[str, Any] | None = None
) -> str:
    """Issue a signed JWT access token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "org_id": settings.DEFAULT_ORG_ID,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
