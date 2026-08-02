from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    ensure_org_admin,
    get_current_user,
    get_org_or_404,
    require_superadmin,
)
from app.core.database import get_db
from app.core.permissions import Role
from app.models import Organization, OrganizationMembership, User
from app.schemas.organization import (
    MemberCreate,
    MembershipOut,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
)
from app.services import resolve_or_create_user

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationOut])
async def list_organizations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Organization]:
    """Superadmins see all organizations; everyone else sees the ones they
    administer."""
    if user.is_superadmin:
        result = await db.execute(select(Organization).order_by(Organization.name))
        return list(result.scalars().all())

    result = await db.execute(
        select(Organization)
        .join(OrganizationMembership)
        .where(OrganizationMembership.user_id == user.id)
        .order_by(Organization.name)
    )
    return list(result.scalars().all())


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    org = Organization(
        name=payload.name,
        email=payload.email,
        contact_person=payload.contact_person,
        country=payload.country,
        created_by_id=admin.id,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    org = await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)
    return org


@router.patch("/{org_id}", response_model=OrganizationOut)
async def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    org = await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    _: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    org = await get_org_or_404(db, org_id)
    await db.delete(org)
    await db.commit()


# --------------------------------------------------------------------------- #
# Organization admins (members)
# --------------------------------------------------------------------------- #
@router.get("/{org_id}/members", response_model=list[MembershipOut])
async def list_members(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationMembership]:
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)
    result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id)
        .options(selectinload(OrganizationMembership.user))
        .order_by(OrganizationMembership.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/{org_id}/members",
    response_model=MembershipOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    org_id: int,
    payload: MemberCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMembership:
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)

    target = await resolve_or_create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )

    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == target.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an admin of this organization",
        )

    membership = OrganizationMembership(
        user_id=target.id,
        organization_id=org_id,
        role=Role.admin.value,
    )
    db.add(membership)
    await db.commit()

    result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.id == membership.id)
        .options(selectinload(OrganizationMembership.user))
    )
    return result.scalar_one()


@router.delete(
    "/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    org_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)

    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    await db.delete(membership)
    await db.commit()
