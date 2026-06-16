"""End-to-end tests that run fully offline (mock LLM + mock search)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents import Orchestrator
from app.export import report_to_markdown, report_to_pdf
from app.main import app


def test_orchestrator_runs_offline():
    report = Orchestrator().run("The Great Gatsby", author="F. Scott Fitzgerald")
    assert report.book.title
    assert isinstance(report.reviews, list)
    assert report.reviews, "mock pipeline should produce reviews"
    # verifier should always return a result
    assert 0.0 <= report.verification.confidence <= 1.0


def test_markdown_export_contains_sections():
    report = Orchestrator().run("Dune")
    md = report_to_markdown(report)
    assert "# " in md
    assert "## Reviews" in md
    assert "## Verification" in md


def test_pdf_export_is_pdf_bytes():
    report = Orchestrator().run("1984")
    pdf = report_to_pdf(report)
    assert pdf[:4] == b"%PDF"


def test_analyze_endpoint():
    client = TestClient(app)
    resp = client.post("/analyze", json={"title": "Brave New World"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["book"]["title"]
    assert "reviews" in data


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
