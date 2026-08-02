"""End-to-end tests covering the role-based access-control flows."""
from __future__ import annotations

import pytest

from tests.conftest import auth_header


async def _login(client, email, password):
    resp = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _create_org(client, token, name="Acme"):
    resp = await client.post(
        "/api/organizations",
        headers=auth_header(token),
        json={
            "name": name,
            "email": f"{name.lower()}@corp.example.com",
            "contact_person": "Jane Doe",
            "country": "US",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
async def test_login_and_me(client, superadmin_token):
    resp = await client.get("/api/me", headers=auth_header(superadmin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_superadmin"] is True
    assert body["primary_role"] == "superadmin"


async def test_login_bad_password(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 401


async def test_refresh_token(client):
    login = await client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "RootPass123"},
    )
    refresh = login.json()["refresh_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# --------------------------------------------------------------------------- #
# Organizations — only superadmin can create
# --------------------------------------------------------------------------- #
async def test_only_superadmin_creates_org(client, superadmin_token):
    # Create a plain user via superadmin.
    resp = await client.post(
        "/api/users",
        headers=auth_header(superadmin_token),
        json={
            "email": "dev@example.com",
            "full_name": "Dev User",
            "password": "DevPass123",
        },
    )
    assert resp.status_code == 201

    dev_token = await _login(client, "dev@example.com", "DevPass123")
    resp = await client.post(
        "/api/organizations",
        headers=auth_header(dev_token),
        json={
            "name": "Rogue",
            "email": "rogue@corp.example.com",
            "contact_person": "X",
            "country": "US",
        },
    )
    assert resp.status_code == 403


async def test_superadmin_creates_org(client, superadmin_token):
    org = await _create_org(client, superadmin_token)
    assert org["name"] == "Acme"
    assert org["country"] == "US"


# --------------------------------------------------------------------------- #
# Admin scope
# --------------------------------------------------------------------------- #
async def test_admin_manages_own_org_only(client, superadmin_token):
    org_a = await _create_org(client, superadmin_token, "OrgA")
    org_b = await _create_org(client, superadmin_token, "OrgB")

    # Make an admin for org A.
    resp = await client.post(
        f"/api/organizations/{org_a['id']}/members",
        headers=auth_header(superadmin_token),
        json={
            "email": "admin_a@example.com",
            "full_name": "Admin A",
            "password": "AdminPass123",
        },
    )
    assert resp.status_code == 201

    admin_token = await _login(client, "admin_a@example.com", "AdminPass123")

    # Admin can read org A.
    resp = await client.get(
        f"/api/organizations/{org_a['id']}", headers=auth_header(admin_token)
    )
    assert resp.status_code == 200

    # But not org B.
    resp = await client.get(
        f"/api/organizations/{org_b['id']}", headers=auth_header(admin_token)
    )
    assert resp.status_code == 403

    # /me reflects the admin role.
    me = await client.get("/api/me", headers=auth_header(admin_token))
    assert me.json()["primary_role"] == "admin"
    assert len(me.json()["admin_organizations"]) == 1

    # Admin cannot delete an org (superadmin only).
    resp = await client.delete(
        f"/api/organizations/{org_a['id']}", headers=auth_header(admin_token)
    )
    assert resp.status_code == 403


async def test_admin_creates_dashboard_and_grants_access(client, superadmin_token):
    org = await _create_org(client, superadmin_token, "DashCorp")
    await client.post(
        f"/api/organizations/{org['id']}/members",
        headers=auth_header(superadmin_token),
        json={
            "email": "admin@dashcorp.com",
            "full_name": "Dash Admin",
            "password": "AdminPass123",
        },
    )
    admin_token = await _login(client, "admin@dashcorp.com", "AdminPass123")

    # Admin creates a dashboard.
    resp = await client.post(
        "/api/dashboards",
        headers=auth_header(admin_token),
        json={
            "organization_id": org["id"],
            "name": "Sales",
            "description": "Sales KPIs",
        },
    )
    assert resp.status_code == 201, resp.text
    dashboard = resp.json()

    # Grant a viewer.
    resp = await client.post(
        f"/api/dashboards/{dashboard['id']}/access",
        headers=auth_header(admin_token),
        json={
            "email": "viewer@dashcorp.com",
            "role": "viewer",
            "full_name": "Vic Viewer",
            "password": "ViewPass123",
        },
    )
    assert resp.status_code == 201, resp.text

    # Grant a developer.
    resp = await client.post(
        f"/api/dashboards/{dashboard['id']}/access",
        headers=auth_header(admin_token),
        json={
            "email": "dev@dashcorp.com",
            "role": "developer",
            "full_name": "Deb Developer",
            "password": "DevPass123",
        },
    )
    assert resp.status_code == 201, resp.text

    # Viewer can read but not edit.
    viewer_token = await _login(client, "viewer@dashcorp.com", "ViewPass123")
    resp = await client.get(
        f"/api/dashboards/{dashboard['id']}", headers=auth_header(viewer_token)
    )
    assert resp.status_code == 200
    resp = await client.patch(
        f"/api/dashboards/{dashboard['id']}",
        headers=auth_header(viewer_token),
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403

    # Developer can edit.
    dev_token = await _login(client, "dev@dashcorp.com", "DevPass123")
    resp = await client.patch(
        f"/api/dashboards/{dashboard['id']}",
        headers=auth_header(dev_token),
        json={"description": "Updated by dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated by dev"

    # Developer cannot manage access or delete.
    resp = await client.post(
        f"/api/dashboards/{dashboard['id']}/access",
        headers=auth_header(dev_token),
        json={"email": "x@dashcorp.com", "role": "viewer",
              "full_name": "X", "password": "XxPass1234"},
    )
    assert resp.status_code == 403
    resp = await client.delete(
        f"/api/dashboards/{dashboard['id']}", headers=auth_header(dev_token)
    )
    assert resp.status_code == 403


async def test_viewer_cannot_see_unrelated_dashboard(client, superadmin_token):
    org = await _create_org(client, superadmin_token, "Isolated")
    # superadmin creates a dashboard directly.
    resp = await client.post(
        "/api/dashboards",
        headers=auth_header(superadmin_token),
        json={"organization_id": org["id"], "name": "Secret"},
    )
    dashboard = resp.json()

    # Create an unrelated user.
    await client.post(
        "/api/users",
        headers=auth_header(superadmin_token),
        json={"email": "nobody@example.com", "full_name": "No Body",
              "password": "NoPass1234"},
    )
    token = await _login(client, "nobody@example.com", "NoPass1234")

    resp = await client.get(
        f"/api/dashboards/{dashboard['id']}", headers=auth_header(token)
    )
    assert resp.status_code == 403

    # And their dashboard list is empty.
    resp = await client.get("/api/dashboards", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_user_can_belong_to_multiple_orgs_and_dashboards(client, superadmin_token):
    org1 = await _create_org(client, superadmin_token, "Multi1")
    org2 = await _create_org(client, superadmin_token, "Multi2")

    for org in (org1, org2):
        resp = await client.post(
            f"/api/organizations/{org['id']}/members",
            headers=auth_header(superadmin_token),
            json={"email": "multi@example.com", "full_name": "Multi Admin",
                  "password": "MultiPass123"},
        )
        assert resp.status_code == 201

    token = await _login(client, "multi@example.com", "MultiPass123")
    me = await client.get("/api/me", headers=auth_header(token))
    assert len(me.json()["admin_organizations"]) == 2

    # Admin of both orgs sees dashboards from both.
    for org in (org1, org2):
        await client.post(
            "/api/dashboards",
            headers=auth_header(token),
            json={"organization_id": org["id"], "name": f"D-{org['name']}"},
        )
    resp = await client.get("/api/dashboards", headers=auth_header(token))
    assert len(resp.json()) == 2
