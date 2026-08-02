from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.permissions import Role
from app.schemas.user import UserOut


class DashboardBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)


class DashboardCreate(DashboardBase):
    organization_id: int


class DashboardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)


class DashboardOut(DashboardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    created_at: datetime
    created_by_id: int | None = None


class DashboardAccessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dashboard_id: int
    role: str
    created_at: datetime
    user: UserOut


class _DashboardRole(BaseModel):
    role: Role

    def as_value(self) -> str:
        return self.role.value


class AccessGrantCreate(BaseModel):
    """Grant a user developer/viewer access to a dashboard.

    Attaches an existing user by ``email`` or creates one from
    ``full_name`` + ``password``.
    """

    email: EmailStr
    role: Role
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AccessGrantUpdate(BaseModel):
    role: Role
