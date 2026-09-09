"""HTTP Basic authentication."""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import get_settings

_security = HTTPBasic()


def require_auth(
    credentials: HTTPBasicCredentials = Depends(_security),
) -> str:
    """Validate HTTP Basic credentials against configured username/password.

    Uses constant-time comparison to avoid timing attacks. Returns the
    authenticated username on success.
    """
    settings = get_settings()

    correct_user = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.auth_username.encode("utf-8"),
    )
    correct_pass = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.auth_password.encode("utf-8"),
    )

    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
