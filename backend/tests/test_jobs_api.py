"""Job status API: polling, SSE, and the Phase 4 non-blocking exit test."""

from __future__ import annotations

import asyncio

from tests import fixtures


def _upload(client, name, data, content_type):
    return client.post("/api/v1/documents", files={"file": (name, data, content_type)})


def test_job_status_polling(upload_client):
    up = _upload(upload_client, "n.md", fixtures.make_markdown(), "text/markdown")
    job_id = up.json()["job"]["id"]
    resp = upload_client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["progress"] == 100
    assert body["stage"] in {"indexing", "embedding", "chunking", "parsing"}


def test_unknown_job_404(upload_client):
    assert upload_client.get("/api/v1/jobs/does-not-exist").status_code == 404


def test_job_sse_stream(upload_client):
    up = _upload(upload_client, "n.md", fixtures.make_markdown(), "text/markdown")
    job_id = up.json()["job"]["id"]
    resp = upload_client.get(f"/api/v1/jobs/{job_id}/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "data:" in resp.text
    assert "completed" in resp.text


def _mixed(i: int) -> tuple[str, bytes, str]:
    body = f"unique document number {i} with distinctive content"
    kind = i % 4
    if kind == 0:
        return f"d{i}.md", fixtures.make_markdown(body=body), "text/markdown"
    if kind == 1:
        return f"d{i}.txt", fixtures.make_text(body), "text/plain"
    if kind == 2:
        return f"d{i}.pdf", fixtures.make_pdf(body), "application/pdf"
    return (
        f"d{i}.docx",
        fixtures.make_docx(body=body),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def test_50_mixed_docs_non_blocking_then_recover(async_env, monkeypatch):
    """Phase 4 exit: 50 mixed-format docs upload without blocking the API
    (fake queue enqueues, ingestion runs later), then all process to completion."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "INGEST_RATE_LIMIT", 1000)
    client = async_env("fake")  # non-blocking: enqueue only, no inline work

    from app.workers.ingest_runner import run_ingest_job

    job_ids: list[str] = []
    doc_ids: list[str] = []
    for i in range(50):
        name, data, ctype = _mixed(i)
        resp = _upload(client, name, data, ctype)
        assert resp.status_code == 202, name
        body = resp.json()
        # API returned immediately without running ingestion.
        assert body["job"]["status"] == "queued"
        assert body["document"]["status"] == "pending"
        job_ids.append(body["job"]["id"])
        doc_ids.append(body["document"]["id"])

    assert len(set(doc_ids)) == 50  # all distinct, no accidental dedup

    # Drain the queue as the worker would; each job runs to completion.
    for doc_id, job_id in zip(doc_ids, job_ids, strict=True):
        status = asyncio.run(run_ingest_job(doc_id, job_id))
        assert status == "completed"

    # Every job is now completed and every document indexed.
    for job_id in job_ids:
        assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "completed"

    # And the corpus is retrievable.
    hits = client.post(
        "/api/v1/documents/search",
        params={"q": "unique document number 7 with distinctive content", "top_k": 5},
    ).json()["hits"]
    assert hits
