"""API integration tests using an isolated in-memory SQLite database.

The LLM dependency is overridden with a disabled stub so tests are fast,
deterministic, and require no API key or network.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.llm import LLMClient, get_llm_client
from app.database import Base, get_db
from app.main import app


class DisabledLLM(LLMClient):
    def __init__(self) -> None:
        pass

    @property
    def enabled(self) -> bool:
        return False


@pytest.fixture
def client() -> TestClient:
    # In-memory SQLite shared across the connection pool for the test session.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_client] = lambda: DisabledLLM()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


VALID_PAYLOAD = {
    "age": 30,
    "sex": "male",
    "height_cm": 180,
    "weight_kg": 80,
    "activity_level": "moderate",
    "goal": "lose_weight",
    "diet_type": "high_protein",
    "meals_per_day": 4,
    "allergies": ["shellfish"],
    "dislikes": [],
    "notes": "prefers quick meals",
}


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_and_fetch_plan(client: TestClient) -> None:
    resp = client.post("/api/v1/plans", json=VALID_PAYLOAD)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    plan_id = body["plan_id"]

    assert body["meal_plan"]["source"] == "fallback"
    assert body["nutrition"]["target_kcal"] > 0
    assert len(body["meal_plan"]["days"]) == 3

    fetched = client.get(f"/api/v1/plans/{plan_id}")
    assert fetched.status_code == 200
    assert fetched.json()["plan_id"] == plan_id


def test_list_and_delete_plan(client: TestClient) -> None:
    created = client.post("/api/v1/plans", json=VALID_PAYLOAD).json()
    plan_id = created["plan_id"]

    listed = client.get("/api/v1/plans")
    assert listed.status_code == 200
    assert any(p["plan_id"] == plan_id for p in listed.json())

    deleted = client.delete(f"/api/v1/plans/{plan_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/plans/{plan_id}").status_code == 404


def test_validation_rejects_bad_input(client: TestClient) -> None:
    bad = {**VALID_PAYLOAD, "weight_kg": 5}  # below the 30kg lower bound
    resp = client.post("/api/v1/plans", json=bad)
    assert resp.status_code == 422


def test_unknown_plan_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/plans/999999").status_code == 404
