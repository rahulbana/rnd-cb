from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.db_connection import DBType


class DBConnectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    db_type: DBType
    host: str = Field(min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)


class DBConnectionCreate(DBConnectionBase):
    password: str = Field(min_length=1, max_length=512)


class DBConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    db_type: DBType | None = None
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    # Only sent when the admin wants to rotate the stored password.
    password: str | None = Field(default=None, min_length=1, max_length=512)


class DBConnectionOut(DBConnectionBase):
    """The password is deliberately omitted; ``has_password`` signals that a
    secret is stored."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    has_password: bool
    created_at: datetime
