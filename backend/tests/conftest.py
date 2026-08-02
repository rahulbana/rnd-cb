from __future__ import annotations

import os

# Configure an isolated in-memory-ish test DB *before* importing the app.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_app.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["FIRST_SUPERADMIN_EMAIL"] = "root@example.com"
os.environ["FIRST_SUPERADMIN_PASSWORD"] = "RootPass123"
os.environ["FIRST_SUPERADMIN_NAME"] = "Root"

import pathlib

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, engine, init_db
from app.main import app
from app.seed import ensure_superadmin


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    # Drop + recreate all tables for each test for full isolation.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    await ensure_superadmin()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def superadmin_token(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "RootPass123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def pytest_sessionfinish(session, exitstatus):
    # Best-effort cleanup of the test DB file.
    db_file = pathlib.Path("test_app.db")
    if db_file.exists():
        db_file.unlink()
