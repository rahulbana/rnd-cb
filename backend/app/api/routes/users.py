from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_dashboard_or_404, get_org_or_404, require_superadmin
from app.core.database import get_db
from app.core.permissions import Role
from app.core.security import hash_password
from app.models import DashboardAccess, OrganizationMembership, User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import get_user_by_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    _: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
    search: str | None = None,
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if search:
        like = f"%{search}%"
        stmt = stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> User:
    if await get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_superadmin=payload.role == Role.superadmin,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # assign user.id for the scope bindings below

    # Attach the new user to an organization / dashboard per their role.
    if payload.role == Role.admin:
        # organization_id is guaranteed present by schema validation.
        await get_org_or_404(db, payload.organization_id)  # type: ignore[arg-type]
        db.add(
            OrganizationMembership(
                user_id=user.id,
                organization_id=payload.organization_id,
                role=Role.admin.value,
            )
        )
    elif payload.role in (Role.developer, Role.viewer):
        if payload.dashboard_id is not None:
            dashboard = await get_dashboard_or_404(db, payload.dashboard_id)
            if (
                payload.organization_id is not None
                and dashboard.organization_id != payload.organization_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dashboard does not belong to the given organization",
                )
            db.add(
                DashboardAccess(
                    user_id=user.id,
                    dashboard_id=dashboard.id,
                    role=payload.role.value,
                )
            )
        elif payload.organization_id is not None:
            # Org given but no dashboard: nothing concrete to grant yet, but
            # make sure the organization actually exists.
            await get_org_or_404(db, payload.organization_id)

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    _: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.is_active is not None:
        # Don't let a superadmin lock themselves out.
        if user.id == current.id and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        user.is_active = payload.is_active
    if payload.is_superadmin is not None:
        if user.id == current.id and payload.is_superadmin is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot revoke your own superadmin role",
            )
        user.is_superadmin = payload.is_superadmin

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
