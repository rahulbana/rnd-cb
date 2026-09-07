"""CORS: the browser frontend must be able to call the API cross-origin."""

from __future__ import annotations


def test_preflight_allows_frontend_origin(client):
    resp = client.options(
        "/api/v1/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_actual_request_carries_cors_header(async_env):
    # Wired offline stack (sqlite) so register actually runs; the CORS header
    # must ride along so the browser exposes the response instead of blocking it.
    client = async_env("inline", authenticate=False)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "cors@example.com", "password": "password123"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code in (200, 201)
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_unlisted_origin_is_not_allowed(client):
    resp = client.options(
        "/api/v1/auth/register",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"
