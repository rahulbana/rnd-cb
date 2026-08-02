from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    ensure_org_admin,
    ensure_org_viewer,
    get_current_user,
    get_org_or_404,
    require_superadmin,
)
from app.core.crypto import encrypt
from app.core.database import get_db
from app.core.permissions import Role
from app.models import (
    Dashboard,
    DashboardAccess,
    DBConnection,
    Organization,
    OrganizationMembership,
    User,
)
from app.schemas.db_connection import (
    DBConnectionCreate,
    DBConnectionOut,
    DBConnectionUpdate,
)
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
    """Organizations the caller can see.

    * superadmin        -> all
    * admin             -> orgs they administer
    * developer/viewer  -> orgs containing a dashboard they've been granted
    """
    if user.is_superadmin:
        result = await db.execute(select(Organization).order_by(Organization.name))
        return list(result.scalars().all())

    # Org ids the user administers.
    admin_ids = set(
        (
            await db.execute(
                select(OrganizationMembership.organization_id).where(
                    OrganizationMembership.user_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )
    # Org ids reachable via a dashboard grant.
    access_ids = set(
        (
            await db.execute(
                select(Dashboard.organization_id)
                .join(DashboardAccess, DashboardAccess.dashboard_id == Dashboard.id)
                .where(DashboardAccess.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    org_ids = admin_ids | access_ids
    if not org_ids:
        return []

    result = await db.execute(
        select(Organization)
        .where(Organization.id.in_(org_ids))
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
    await db.flush()  # assign org.id before attaching admins

    # Attach the (>=1) admins. Each entry resolves an existing user or creates
    # a new one; duplicates within the same request are ignored.
    seen: set[int] = set()
    for entry in payload.admins:
        target = await resolve_or_create_user(
            db,
            email=entry.email,
            full_name=entry.full_name,
            password=entry.password,
        )
        if target.id in seen:
            continue
        seen.add(target.id)
        db.add(
            OrganizationMembership(
                user_id=target.id,
                organization_id=org.id,
                role=Role.admin.value,
            )
        )

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
    # Admins manage the org; viewers/developers may read it to browse dashboards.
    await ensure_org_viewer(db, user, org_id)
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


# --------------------------------------------------------------------------- #
# Database connections (org admins only). One org -> many connections.
# --------------------------------------------------------------------------- #
def _connection_out(conn: DBConnection) -> DBConnectionOut:
    return DBConnectionOut(
        id=conn.id,
        organization_id=conn.organization_id,
        name=conn.name,
        db_type=conn.db_type,  # type: ignore[arg-type]
        host=conn.host,
        port=conn.port,
        database=conn.database,
        username=conn.username,
        has_password=bool(conn.password_encrypted),
        created_at=conn.created_at,
    )


async def _get_connection_or_404(
    db: AsyncSession, org_id: int, conn_id: int
) -> DBConnection:
    conn = await db.get(DBConnection, conn_id)
    if conn is None or conn.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.get("/{org_id}/connections", response_model=list[DBConnectionOut])
async def list_connections(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DBConnectionOut]:
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)
    result = await db.execute(
        select(DBConnection)
        .where(DBConnection.organization_id == org_id)
        .order_by(DBConnection.created_at)
    )
    return [_connection_out(c) for c in result.scalars().all()]


@router.post(
    "/{org_id}/connections",
    response_model=DBConnectionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    org_id: int,
    payload: DBConnectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DBConnectionOut:
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)

    conn = DBConnection(
        organization_id=org_id,
        name=payload.name,
        db_type=payload.db_type.value,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        password_encrypted=encrypt(payload.password),
        created_by_id=user.id,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return _connection_out(conn)


@router.patch(
    "/{org_id}/connections/{conn_id}", response_model=DBConnectionOut
)
async def update_connection(
    org_id: int,
    conn_id: int,
    payload: DBConnectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DBConnectionOut:
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)
    conn = await _get_connection_or_404(db, org_id, conn_id)

    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        secret = data.pop("password")
        if secret:  # only rotate when a non-empty password is supplied
            conn.password_encrypted = encrypt(secret)
    if "db_type" in data and data["db_type"] is not None:
        data["db_type"] = data["db_type"].value
    for field, value in data.items():
        setattr(conn, field, value)

    await db.commit()
    await db.refresh(conn)
    return _connection_out(conn)


@router.delete(
    "/{org_id}/connections/{conn_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_connection(
    org_id: int,
    conn_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_or_404(db, org_id)
    await ensure_org_admin(db, user, org_id)
    conn = await _get_connection_or_404(db, org_id, conn_id)
    await db.delete(conn)
    await db.commit()
