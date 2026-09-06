"""API skeleton tests: health, readiness, provider wiring, error shape."""

from __future__ import annotations


def test_health_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_ready_ok(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_providers_reflects_config(client):
    resp = client.get("/api/v1/providers")
    assert resp.status_code == 200
    body = resp.json()
    # Every port is present in the live wiring diagram.
    for port in (
        "llm",
        "embedder",
        "vector_store",
        "reranker",
        "retriever",
        "parser",
        "chunker",
        "storage",
        "task_queue",
    ):
        assert port in body


def test_unknown_route_returns_structured_error(client):
    resp = client.get("/api/v1/nope")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "http_error"
