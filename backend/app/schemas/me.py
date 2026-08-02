from __future__ import annotations

from pydantic import BaseModel

from app.schemas.user import UserOut


class OrgMembershipSummary(BaseModel):
    organization_id: int
    organization_name: str
    role: str


class DashboardAccessSummary(BaseModel):
    dashboard_id: int
    dashboard_name: str
    organization_id: int
    organization_name: str
    role: str


class MeResponse(BaseModel):
    """Current user's profile plus everything the frontend needs to render
    role-aware navigation."""

    user: UserOut
    is_superadmin: bool
    # A convenience "primary" role label for UI badges.
    primary_role: str
    permissions: list[str]
    admin_organizations: list[OrgMembershipSummary]
    dashboard_access: list[DashboardAccessSummary]
