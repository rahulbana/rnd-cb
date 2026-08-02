"""Fixed role -> permission mapping.

The set of permissions each role holds is hardcoded here (that is what
"fixed roles" means). What is *dynamic* is the assignment of users to roles
within a given scope (application / organization / dashboard), which is
managed at runtime by superadmins and organization admins.

Scopes
------
* Application level : ``superadmin`` — full control, creates organizations.
* Organization level: ``admin``      — every permission inside an org.
* Dashboard level   : ``developer``  — read + edit a dashboard's content.
                      ``viewer``      — read a dashboard only.
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    superadmin = "superadmin"
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class Permission(str, Enum):
    # --- Application scope (superadmin only) ---
    ORG_CREATE = "org:create"
    ORG_DELETE = "org:delete"
    USER_MANAGE_GLOBAL = "user:manage_global"
    ROLE_MANAGE = "role:manage"

    # --- Organization scope (admin within their org) ---
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_MANAGE_MEMBERS = "org:manage_members"
    DASHBOARD_CREATE = "dashboard:create"
    DASHBOARD_DELETE = "dashboard:delete"
    DASHBOARD_MANAGE_ACCESS = "dashboard:manage_access"

    # --- Dashboard scope ---
    DASHBOARD_READ = "dashboard:read"
    DASHBOARD_UPDATE = "dashboard:update"


# Superadmin implicitly holds every permission.
SUPERADMIN_PERMISSIONS: frozenset[Permission] = frozenset(Permission)

ORG_ADMIN_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.ORG_READ,
        Permission.ORG_UPDATE,
        Permission.ORG_MANAGE_MEMBERS,
        Permission.DASHBOARD_CREATE,
        Permission.DASHBOARD_DELETE,
        Permission.DASHBOARD_MANAGE_ACCESS,
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_UPDATE,
    }
)

DASHBOARD_DEVELOPER_PERMISSIONS: frozenset[Permission] = frozenset(
    {Permission.DASHBOARD_READ, Permission.DASHBOARD_UPDATE}
)

DASHBOARD_VIEWER_PERMISSIONS: frozenset[Permission] = frozenset(
    {Permission.DASHBOARD_READ}
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.superadmin: SUPERADMIN_PERMISSIONS,
    Role.admin: ORG_ADMIN_PERMISSIONS,
    Role.developer: DASHBOARD_DEVELOPER_PERMISSIONS,
    Role.viewer: DASHBOARD_VIEWER_PERMISSIONS,
}

# Ordering used to compare dashboard-level access (developer outranks viewer).
DASHBOARD_ROLE_RANK: dict[str, int] = {
    Role.viewer.value: 1,
    Role.developer.value: 2,
}


def permissions_for(role: Role | str) -> frozenset[Permission]:
    role = Role(role)
    return ROLE_PERMISSIONS[role]
