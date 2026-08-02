"""Auth + authorization dependencies and helpers.

Authorization is resolved *per scope*:

* ``get_current_user``    — authenticates the bearer token.
* ``require_superadmin``  — application scope.
* ``ensure_org_admin``    — organization scope (superadmin or org admin member).
* ``ensure_dashboard_role`` — dashboard scope (superadmin, org admin of the
  owning org, or a direct developer/viewer grant of sufficient rank).
"""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    DASHBOARD_ROLE_RANK,
    Permission,
    Role,
    permissions_for,
)
from app.core.security import decode_token
from app.models import (
    Dashboard,
    DashboardAccess,
    Organization,
    OrganizationMembership,
    User,
)

_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _CREDENTIALS_EXC from exc

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXC

    sub = payload.get("sub")
    if sub is None:
        raise _CREDENTIALS_EXC

    user = await db.get(User, int(sub))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required",
        )
    return user


# --------------------------------------------------------------------------- #
# Fetch-or-404 helpers
# --------------------------------------------------------------------------- #
async def get_org_or_404(db: AsyncSession, org_id: int) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def get_dashboard_or_404(db: AsyncSession, dashboard_id: int) -> Dashboard:
    dashboard = await db.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


# --------------------------------------------------------------------------- #
# Scope resolution
# --------------------------------------------------------------------------- #
async def is_org_admin(db: AsyncSession, user: User, org_id: int) -> bool:
    if user.is_superadmin:
        return True
    result = await db.execute(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def ensure_org_admin(db: AsyncSession, user: User, org_id: int) -> None:
    if not await is_org_admin(db, user, org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin privileges required",
        )


async def dashboard_access_role(
    db: AsyncSession, user: User, dashboard: Dashboard
) -> Role | None:
    """Return the user's effective role on a dashboard, or None if no access.

    Superadmin / org-admin resolve to ``admin`` (full access); otherwise the
    direct grant (developer/viewer) is returned.
    """
    if user.is_superadmin:
        return Role.admin
    if await is_org_admin(db, user, dashboard.organization_id):
        return Role.admin
    result = await db.execute(
        select(DashboardAccess.role).where(
            DashboardAccess.user_id == user.id,
            DashboardAccess.dashboard_id == dashboard.id,
        )
    )
    role_value = result.scalar_one_or_none()
    return Role(role_value) if role_value is not None else None


def _dashboard_rank(role: Role) -> int:
    # admin outranks developer/viewer for read/update purposes.
    if role == Role.admin:
        return 99
    return DASHBOARD_ROLE_RANK.get(role.value, 0)


async def ensure_dashboard_role(
    db: AsyncSession,
    user: User,
    dashboard: Dashboard,
    minimum: Role,
) -> Role:
    """Ensure the user holds at least ``minimum`` role on the dashboard."""
    role = await dashboard_access_role(db, user, dashboard)
    if role is None or _dashboard_rank(role) < _dashboard_rank(minimum):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient dashboard permissions",
        )
    return role


async def ensure_dashboard_manage(
    db: AsyncSession, user: User, dashboard: Dashboard
) -> None:
    """Managing access / deleting a dashboard requires org-admin scope."""
    await ensure_org_admin(db, user, dashboard.organization_id)


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
