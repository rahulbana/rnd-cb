from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, permissions_for
from app.models import Dashboard, DashboardAccess, OrganizationMembership, User
from app.schemas.me import (
    DashboardAccessSummary,
    MeResponse,
    OrgMembershipSummary,
)
from app.schemas.user import UserOut

router = APIRouter(tags=["me"])


def _primary_role(is_superadmin: bool, admin_orgs: list, dashboard_roles: list[str]) -> str:
    if is_superadmin:
        return Role.superadmin.value
    if admin_orgs:
        return Role.admin.value
    if Role.developer.value in dashboard_roles:
        return Role.developer.value
    if Role.viewer.value in dashboard_roles:
        return Role.viewer.value
    return "none"


@router.get("/me", response_model=MeResponse)
async def read_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    # Admin org memberships (with organization eager-loaded).
    mem_result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user.id)
        .options(selectinload(OrganizationMembership.organization))
    )
    memberships = mem_result.scalars().all()
    admin_orgs = [
        OrgMembershipSummary(
            organization_id=m.organization_id,
            organization_name=m.organization.name,
            role=m.role,
        )
        for m in memberships
    ]

    # Direct dashboard grants (with dashboard + org eager-loaded).
    access_result = await db.execute(
        select(DashboardAccess)
        .where(DashboardAccess.user_id == user.id)
        .options(
            selectinload(DashboardAccess.dashboard).selectinload(
                Dashboard.organization
            )
        )
    )
    grants = access_result.scalars().all()
    dashboard_access = [
        DashboardAccessSummary(
            dashboard_id=g.dashboard_id,
            dashboard_name=g.dashboard.name,
            organization_id=g.dashboard.organization_id,
            organization_name=g.dashboard.organization.name,
            role=g.role,
        )
        for g in grants
    ]

    dashboard_roles = [g.role for g in grants]
    primary = _primary_role(user.is_superadmin, admin_orgs, dashboard_roles)

    # Permissions shown are the union at the user's highest scope, for UI hints.
    perms: set[str] = set()
    if user.is_superadmin:
        perms |= {p.value for p in permissions_for(Role.superadmin)}
    if admin_orgs:
        perms |= {p.value for p in permissions_for(Role.admin)}
    for r in set(dashboard_roles):
        perms |= {p.value for p in permissions_for(Role(r))}

    return MeResponse(
        user=UserOut.model_validate(user),
        is_superadmin=user.is_superadmin,
        primary_role=primary,
        permissions=sorted(perms),
        admin_organizations=admin_orgs,
        dashboard_access=dashboard_access,
    )
