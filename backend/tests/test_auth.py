"""Auth: register/login/refresh, RBAC, API keys, and protected routes."""

from __future__ import annotations


def _register(client, email, password="password123"):
    return client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


def test_register_login_me(async_env):
    client = async_env("inline", authenticate=False)
    reg = _register(client, "alice@example.com")
    assert reg.status_code == 201
    body = reg.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "admin"  # first user bootstraps as admin

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_duplicate_email_rejected(async_env):
    client = async_env("inline", authenticate=False)
    _register(client, "dup@example.com")
    assert _register(client, "dup@example.com").status_code == 409


def test_wrong_password_401(async_env):
    client = async_env("inline", authenticate=False)
    _register(client, "bob@example.com")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_second_user_is_not_admin(async_env):
    client = async_env("inline", authenticate=False)
    _register(client, "first@example.com")
    second = _register(client, "second@example.com")
    assert second.json()["user"]["role"] == "user"


def test_refresh_returns_new_access_token(async_env):
    client = async_env("inline", authenticate=False)
    tokens = _register(client, "carol@example.com").json()
    resp = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_access_token_rejected_as_refresh(async_env):
    client = async_env("inline", authenticate=False)
    tokens = _register(client, "dave@example.com").json()
    # Using an access token where a refresh token is required must fail.
    resp = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert resp.status_code == 401


def test_protected_routes_require_auth(async_env):
    client = async_env("inline", authenticate=False)
    assert client.get("/api/v1/documents").status_code == 401
    assert client.post("/api/v1/chat", json={"question": "hi"}).status_code == 401
    assert client.get("/api/v1/conversations").status_code == 401


def test_api_key_auth(async_env):
    client = async_env("inline")  # already authenticated as admin
    created = client.post("/api/v1/auth/api-keys", json={"scopes": "read"})
    assert created.status_code == 201
    raw = created.json()["api_key"]
    assert raw.startswith("rag_")

    # A fresh client (no bearer) can authenticate with the API key.
    from fastapi.testclient import TestClient

    from app.main import create_app

    bare = TestClient(create_app())
    resp = bare.get("/api/v1/documents", headers={"X-API-Key": raw})
    assert resp.status_code == 200

    listed = client.get("/api/v1/auth/api-keys").json()
    assert len(listed) == 1


def test_health_is_public(client):
    # Health endpoints stay unauthenticated.
    assert client.get("/api/v1/health").status_code == 200
