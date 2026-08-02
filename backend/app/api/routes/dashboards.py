from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    ensure_dashboard_manage,
    ensure_dashboard_role,
    ensure_org_admin,
    get_current_user,
    get_dashboard_or_404,
)
from app.core.database import get_db
from app.core.permissions import Role
from app.models import (
    Dashboard,
    DashboardAccess,
    OrganizationMembership,
    User,
)
from app.schemas.dashboard import (
    AccessGrantCreate,
    AccessGrantUpdate,
    DashboardAccessOut,
    DashboardCreate,
    DashboardOut,
    DashboardUpdate,
)
from app.services import resolve_or_create_user

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

_DASHBOARD_GRANT_ROLES = {Role.developer, Role.viewer}


@router.get("", response_model=list[DashboardOut])
async def list_dashboards(
    organization_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Dashboard]:
    """Dashboards visible to the caller.

    * superadmin: all (optionally filtered by organization)
    * org admin : all dashboards in orgs they administer
    * others    : dashboards with a direct developer/viewer grant
    """
    if user.is_superadmin:
        stmt = select(Dashboard)
        if organization_id is not None:
            stmt = stmt.where(Dashboard.organization_id == organization_id)
        result = await db.execute(stmt.order_by(Dashboard.name))
        return list(result.scalars().all())

    # Orgs the user administers.
    admin_org_rows = await db.execute(
        select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == user.id
        )
    )
    admin_org_ids = set(admin_org_rows.scalars().all())

    # Dashboards with a direct grant.
    grant_rows = await db.execute(
        select(DashboardAccess.dashboard_id).where(
            DashboardAccess.user_id == user.id
        )
    )
    granted_ids = set(grant_rows.scalars().all())

    conditions = []
    if admin_org_ids:
        conditions.append(Dashboard.organization_id.in_(admin_org_ids))
    if granted_ids:
        conditions.append(Dashboard.id.in_(granted_ids))

    if not conditions:
        return []

    stmt = select(Dashboard).where(or_(*conditions))
    if organization_id is not None:
        stmt = stmt.where(Dashboard.organization_id == organization_id)
    result = await db.execute(stmt.order_by(Dashboard.name))
    return list(result.scalars().all())


@router.post("", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    payload: DashboardCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dashboard:
    # Must be admin of the target organization.
    await ensure_org_admin(db, user, payload.organization_id)

    dashboard = Dashboard(
        organization_id=payload.organization_id,
        name=payload.name,
        description=payload.description,
        created_by_id=user.id,
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    return dashboard


@router.get("/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(
    dashboard_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dashboard:
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    await ensure_dashboard_role(db, user, dashboard, Role.viewer)
    return dashboard


@router.patch("/{dashboard_id}", response_model=DashboardOut)
async def update_dashboard(
    dashboard_id: int,
    payload: DashboardUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dashboard:
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    # developer or above may edit the dashboard's content.
    await ensure_dashboard_role(db, user, dashboard, Role.developer)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dashboard, field, value)

    await db.commit()
    await db.refresh(dashboard)
    return dashboard


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    await ensure_dashboard_manage(db, user, dashboard)  # org admin only
    await db.delete(dashboard)
    await db.commit()


# --------------------------------------------------------------------------- #
# Dashboard access grants (developer / viewer)
# --------------------------------------------------------------------------- #
@router.get("/{dashboard_id}/access", response_model=list[DashboardAccessOut])
async def list_access(
    dashboard_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DashboardAccess]:
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    await ensure_dashboard_manage(db, user, dashboard)
    result = await db.execute(
        select(DashboardAccess)
        .where(DashboardAccess.dashboard_id == dashboard_id)
        .options(selectinload(DashboardAccess.user))
        .order_by(DashboardAccess.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/{dashboard_id}/access",
    response_model=DashboardAccessOut,
    status_code=status.HTTP_201_CREATED,
)
async def grant_access(
    dashboard_id: int,
    payload: AccessGrantCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardAccess:
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    await ensure_dashboard_manage(db, user, dashboard)

    if payload.role not in _DASHBOARD_GRANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dashboard grants must be 'developer' or 'viewer'",
        )

    target = await resolve_or_create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )

    existing = await db.execute(
        select(DashboardAccess).where(
            DashboardAccess.user_id == target.id,
            DashboardAccess.dashboard_id == dashboard_id,
        )
    )
    grant = existing.scalar_one_or_none()
    if grant is not None:
        # Idempotent: update the role instead of failing.
        grant.role = payload.role.value
    else:
        grant = DashboardAccess(
            user_id=target.id,
            dashboard_id=dashboard_id,
            role=payload.role.value,
        )
        db.add(grant)
    await db.commit()

    result = await db.execute(
        select(DashboardAccess)
        .where(DashboardAccess.id == grant.id)
        .options(selectinload(DashboardAccess.user))
    )
    return result.scalar_one()


@router.patch(
    "/{dashboard_id}/access/{user_id}", response_model=DashboardAccessOut
)
async def update_access(
    dashboard_id: int,
    user_id: int,
    payload: AccessGrantUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardAccess:
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    await ensure_dashboard_manage(db, user, dashboard)

    if payload.role not in _DASHBOARD_GRANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dashboard grants must be 'developer' or 'viewer'",
        )

    result = await db.execute(
        select(DashboardAccess)
        .where(
            DashboardAccess.dashboard_id == dashboard_id,
            DashboardAccess.user_id == user_id,
        )
        .options(selectinload(DashboardAccess.user))
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=404, detail="Access grant not found")

    grant.role = payload.role.value
    await db.commit()
    await db.refresh(grant)
    return grant


@router.delete(
    "/{dashboard_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_access(
    dashboard_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dashboard = await get_dashboard_or_404(db, dashboard_id)
    await ensure_dashboard_manage(db, user, dashboard)

    result = await db.execute(
        select(DashboardAccess).where(
            DashboardAccess.dashboard_id == dashboard_id,
            DashboardAccess.user_id == user_id,
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=404, detail="Access grant not found")

    await db.delete(grant)
    await db.commit()
