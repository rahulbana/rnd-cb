from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.permissions import Role


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    # Every new user is assigned a role. Optionally they can be attached to an
    # organization / dashboard as part of creation:
    #   * superadmin -> application scope (organization/dashboard ignored)
    #   * admin      -> requires organization_id (added as an org admin)
    #   * developer  -> optional dashboard_id grant (developer access)
    #   * viewer     -> optional dashboard_id grant (viewer access)
    role: Role = Role.viewer
    organization_id: int | None = None
    dashboard_id: int | None = None

    @model_validator(mode="after")
    def _check_scope(self) -> "UserCreate":
        if self.role == Role.admin and self.organization_id is None:
            raise ValueError("The 'admin' role requires an organization_id")
        if self.role == Role.superadmin:
            # Application-scoped role: ignore any org/dashboard hints.
            self.organization_id = None
            self.dashboard_id = None
        return self


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
    is_superadmin: bool | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_superadmin: bool
    is_active: bool
    created_at: datetime
