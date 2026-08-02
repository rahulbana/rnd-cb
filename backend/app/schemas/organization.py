from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserOut


class MemberCreate(BaseModel):
    """Add an admin to an organization.

    If a user with ``email`` already exists they are attached; otherwise a new
    user is created from ``full_name`` + ``password``.
    """

    email: EmailStr
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class OrganizationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    contact_person: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=100)


class OrganizationCreate(OrganizationBase):
    # An organization must be created with at least one admin. Each entry
    # attaches an existing user (by email) or creates a new one.
    admins: list[MemberCreate] = Field(min_length=1)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    contact_person: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=1, max_length=100)


class OrganizationOut(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    created_by_id: int | None = None


class MembershipOut(BaseModel):
    """An organization admin membership, with the user embedded."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    role: str
    created_at: datetime
    user: UserOut
