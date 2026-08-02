"""Tests for org DB connections and viewer/developer org browsing."""
from __future__ import annotations

from tests.conftest import auth_header
from tests.test_rbac import _create_org, _login


async def _make_admin(client, superadmin_token, org, email):
    resp = await client.post(
        f"/api/organizations/{org['id']}/members",
        headers=auth_header(superadmin_token),
        json={"email": email, "full_name": "Org Admin", "password": "AdminPass123"},
    )
    assert resp.status_code == 201, resp.text
    return await _login(client, email, "AdminPass123")


# --------------------------------------------------------------------------- #
# DB connections
# --------------------------------------------------------------------------- #
async def test_admin_crud_db_connections(client, superadmin_token):
    org = await _create_org(client, superadmin_token, "ConnCorp")
    admin_token = await _make_admin(client, superadmin_token, org, "connadmin@example.com")

    # Create.
    resp = await client.post(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(admin_token),
        json={
            "name": "Primary",
            "db_type": "postgres",
            "host": "db.internal",
            "port": 5432,
            "database": "app",
            "username": "svc",
            "password": "s3cr3t",
        },
    )
    assert resp.status_code == 201, resp.text
    conn = resp.json()
    assert conn["db_type"] == "postgres"
    assert conn["has_password"] is True
    # The password is never returned.
    assert "password" not in conn

    # A second connection for the same org is allowed.
    resp = await client.post(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(admin_token),
        json={
            "name": "Analytics",
            "db_type": "mysql",
            "host": "mysql.internal",
            "database": "analytics",
            "username": "ro",
            "password": "pw",
        },
    )
    assert resp.status_code == 201

    # List returns both, still no passwords.
    resp = await client.get(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    conns = resp.json()
    assert len(conns) == 2
    assert all("password" not in c for c in conns)

    # Update (rotate password + change host).
    resp = await client.patch(
        f"/api/organizations/{org['id']}/connections/{conn['id']}",
        headers=auth_header(admin_token),
        json={"host": "db2.internal", "password": "newsecret"},
    )
    assert resp.status_code == 200
    assert resp.json()["host"] == "db2.internal"

    # Delete.
    resp = await client.delete(
        f"/api/organizations/{org['id']}/connections/{conn['id']}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 204
    resp = await client.get(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(admin_token),
    )
    assert len(resp.json()) == 1


async def test_stored_password_is_encrypted_and_recoverable(client, superadmin_token):
    """The stored ciphertext is not the plaintext, but decrypts back to it."""
    org = await _create_org(client, superadmin_token, "CryptoCorp")
    admin_token = await _make_admin(client, superadmin_token, org, "crypto@example.com")
    await client.post(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(admin_token),
        json={
            "name": "Vault",
            "db_type": "mssql",
            "host": "h",
            "database": "d",
            "username": "u",
            "password": "plaintext-pw",
        },
    )

    # Inspect storage directly.
    from sqlalchemy import select

    from app.core.crypto import decrypt
    from app.core.database import AsyncSessionLocal
    from app.models import DBConnection

    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(DBConnection))).scalars().first()
        assert row is not None
        assert row.password_encrypted != "plaintext-pw"
        assert decrypt(row.password_encrypted) == "plaintext-pw"


async def test_viewer_cannot_manage_connections(client, superadmin_token):
    org = await _create_org(client, superadmin_token, "SecureCorp")
    dash = await client.post(
        "/api/dashboards",
        headers=auth_header(superadmin_token),
        json={"organization_id": org["id"], "name": "D"},
    )
    dashboard = dash.json()
    # Grant a viewer.
    await client.post(
        f"/api/dashboards/{dashboard['id']}/access",
        headers=auth_header(superadmin_token),
        json={
            "email": "v@example.com",
            "role": "viewer",
            "full_name": "V",
            "password": "ViewPass123",
        },
    )
    viewer_token = await _login(client, "v@example.com", "ViewPass123")

    resp = await client.get(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(viewer_token),
    )
    assert resp.status_code == 403
    resp = await client.post(
        f"/api/organizations/{org['id']}/connections",
        headers=auth_header(viewer_token),
        json={
            "name": "x",
            "db_type": "postgres",
            "host": "h",
            "database": "d",
            "username": "u",
            "password": "p",
        },
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# Viewer / developer org browsing
# --------------------------------------------------------------------------- #
async def test_viewer_sees_org_and_its_dashboards(client, superadmin_token):
    org = await _create_org(client, superadmin_token, "BrowseCorp")
    # Two dashboards; viewer is only granted one.
    d1 = (
        await client.post(
            "/api/dashboards",
            headers=auth_header(superadmin_token),
            json={"organization_id": org["id"], "name": "Granted"},
        )
    ).json()
    await client.post(
        "/api/dashboards",
        headers=auth_header(superadmin_token),
        json={"organization_id": org["id"], "name": "Hidden"},
    )
    await client.post(
        f"/api/dashboards/{d1['id']}/access",
        headers=auth_header(superadmin_token),
        json={
            "email": "browser@example.com",
            "role": "viewer",
            "full_name": "Browser",
            "password": "BrowsePass1",
        },
    )
    token = await _login(client, "browser@example.com", "BrowsePass1")

    # The viewer now sees the org as a card.
    orgs = await client.get("/api/organizations", headers=auth_header(token))
    assert orgs.status_code == 200
    assert [o["id"] for o in orgs.json()] == [org["id"]]

    # They can read basic org info to render the drill-down header.
    resp = await client.get(
        f"/api/organizations/{org['id']}", headers=auth_header(token)
    )
    assert resp.status_code == 200

    # Drilling into the org shows only the dashboard they were granted.
    dashes = await client.get(
        f"/api/dashboards?organization_id={org['id']}", headers=auth_header(token)
    )
    assert dashes.status_code == 200
    names = [d["name"] for d in dashes.json()]
    assert names == ["Granted"]


async def test_unrelated_user_cannot_read_org(client, superadmin_token):
    org = await _create_org(client, superadmin_token, "PrivateCorp")
    await client.post(
        "/api/users",
        headers=auth_header(superadmin_token),
        json={
            "email": "stranger@example.com",
            "full_name": "Stranger",
            "password": "Stranger123",
            "role": "viewer",
        },
    )
    token = await _login(client, "stranger@example.com", "Stranger123")

    resp = await client.get(
        f"/api/organizations/{org['id']}", headers=auth_header(token)
    )
    assert resp.status_code == 403
    orgs = await client.get("/api/organizations", headers=auth_header(token))
    assert orgs.json() == []
