"""Symmetric encryption for secrets stored at rest (DB-connection passwords).

Uses Fernet (AES-128-CBC + HMAC). The key comes from ``ENCRYPTION_KEY`` if set,
otherwise it is deterministically derived from ``JWT_SECRET`` so local dev needs
zero extra configuration.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    if settings.encryption_key:
        key = settings.encryption_key.encode("utf-8")
    else:
        digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a stored secret. Returns "" if the ciphertext can't be read
    (e.g. the key changed) rather than raising."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
