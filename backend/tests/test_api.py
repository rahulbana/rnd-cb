"""API-level tests using FastAPI's TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body and "model" in body


def test_create_study_plan(client, stub_llm, no_research):
    res = client.post(
        "/api/study-plan",
        json={"grade": 9, "subject": "Math", "topic": "Quadratics",
              "duration_weeks": 2, "hours_per_week": 5},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["outline"]["title"] == "Mastering Quadratics"
    assert body["quiz"]["mcqs"]


def test_pdf_export(client, sample_plan):
    res = client.post("/api/study-plan/pdf", json=sample_plan.model_dump())
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.headers["content-disposition"].endswith('.pdf"')
    assert res.content[:5] == b"%PDF-"


def test_missing_api_key_returns_503(client, no_research, monkeypatch):
    """Without an OpenAI key (and without stubbing the LLM) we get a clean 503."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    try:
        res = client.post(
            "/api/study-plan",
            json={"grade": 9, "subject": "Math", "topic": "Quadratics"},
        )
        assert res.status_code == 503
        assert res.json()["error"]["type"] == "configuration_error"
    finally:
        get_settings.cache_clear()


def test_validation_error(client):
    # grade out of allowed range -> 422 from pydantic validation
    res = client.post("/api/study-plan", json={"grade": 99, "subject": "X", "topic": "Y"})
    assert res.status_code == 422
