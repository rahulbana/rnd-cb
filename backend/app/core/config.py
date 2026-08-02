"""Application configuration, loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RBAC Dashboard Platform"

    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Auth / JWT
    jwt_secret: str = "change-me-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Symmetric key used to encrypt stored DB-connection passwords at rest.
    # If unset, a key is derived from `jwt_secret` (fine for local dev; set an
    # explicit Fernet key in production so rotating the JWT secret doesn't make
    # stored secrets undecryptable).
    encryption_key: str | None = None

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Bootstrap superadmin (created once on first startup if it doesn't exist)
    first_superadmin_email: str = "admin@example.com"
    first_superadmin_password: str = "Admin@12345"
    first_superadmin_name: str = "Super Admin"


@lru_cache
def get_settings() -> Settings:
    return Settings()
