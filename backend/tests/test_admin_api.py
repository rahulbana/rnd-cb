"""Admin dashboard, analytics, feedback, and the Phase 9 exit test."""

from __future__ import annotations

import pytest

from tests import fixtures


def _ingest(client, name, body):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, fixtures.make_markdown(body=body), "text/markdown")},
    )


def _chat(client, question):
    return client.post("/api/v1/chat", json={"question": question})


def test_admin_endpoints_require_admin(async_env):
    # Second user is a regular user, not admin.
    client = async_env("inline", authenticate=False)
    client.post(
        "/api/v1/auth/register", json={"email": "admin@x.com", "password": "password123"}
    )
    reg = client.post(
        "/api/v1/auth/register", json={"email": "user@x.com", "password": "password123"}
    )
    token = reg.json()["access_token"]  # second user (role=user)
    client.headers["Authorization"] = f"Bearer {token}"
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.get("/api/v1/admin/analytics").status_code == 403


def test_admin_dashboard(upload_client):
    # upload_client is authenticated as the first user (admin).
    _ingest(upload_client, "d.md", "alpha beta gamma content here")
    _chat(upload_client, "tell me about alpha")

    users = upload_client.get("/api/v1/admin/users").json()
    assert any(u["role"] == "admin" for u in users)

    providers = upload_client.get("/api/v1/admin/providers").json()
    assert providers["llm"] == "fake"
    assert "tracer" in providers and "eval_harness" in providers

    queue = upload_client.get("/api/v1/admin/queue").json()
    assert "by_status" in queue and "by_stage" in queue
    assert queue["by_status"].get("completed", 0) >= 1


def test_analytics(upload_client):
    _ingest(upload_client, "d.md", "quarterly revenue grew twenty percent this year")
    _chat(upload_client, "how did revenue grow")

    analytics = upload_client.get("/api/v1/admin/analytics").json()
    assert analytics["messages"] >= 1
    assert analytics["conversations"] >= 1
    assert isinstance(analytics["cost_by_provider"], list)
    assert "latency_p95_ms" in analytics
    assert "top_documents" in analytics


def test_reprocess_document(upload_client):
    up = _ingest(upload_client, "d.md", "content to reprocess").json()
    doc_id = up["document"]["id"]
    resp = upload_client.post(f"/api/v1/admin/documents/{doc_id}/reprocess")
    assert resp.status_code == 200
    # Inline queue -> reprocess completes immediately.
    assert resp.json()["job"]["status"] == "completed"


def test_feedback_and_analytics_counts(upload_client):
    _ingest(upload_client, "d.md", "alpha content")
    chat = _chat(upload_client, "about alpha").json()
    conv_id = chat["conversation_id"]
    messages = upload_client.get(f"/api/v1/conversations/{conv_id}/messages").json()
    assistant = next(m for m in messages if m["role"] == "assistant")

    resp = upload_client.post(
        "/api/v1/feedback",
        json={"message_id": assistant["id"], "rating": 1, "note": "good"},
    )
    assert resp.status_code == 201
    analytics = upload_client.get("/api/v1/admin/analytics").json()
    assert analytics["feedback_up"] >= 1


@pytest.mark.eval
def test_exit_scorecard_and_traceability(upload_client):
    """Phase 9 exit: an eval run produces a pass/fail scorecard, and any answer
    traces to its retrieved chunks, reranker scores, and prompt version."""
    # Ingest documents that answer the default golden set.
    _ingest(upload_client, "bio.md", "the mitochondria is the powerhouse of the cell")
    _ingest(upload_client, "fin.md", "revenue grew twenty percent last year")

    # 1. Eval run -> scorecard with a pass/fail threshold.
    card = upload_client.post("/api/v1/admin/eval/run").json()
    assert card["harness"] == "heuristic"
    assert card["cases"] == 2
    assert "passed" in card
    assert card["threshold"] == 0.6
    names = {m["name"] for m in card["metrics"]}
    assert names == {
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    }

    # 2. Traceability: a chat answer -> its trace (chunks, scores, prompt version).
    chat = _chat(upload_client, "what is the powerhouse of the cell").json()
    conv_id = chat["conversation_id"]
    messages = upload_client.get(f"/api/v1/conversations/{conv_id}/messages").json()
    assistant = next(m for m in messages if m["role"] == "assistant")

    trace = upload_client.get(f"/api/v1/messages/{assistant['id']}/trace").json()
    assert trace["prompt_version"] == "v1"
    assert trace["provider"] == "fake"
    assert trace["citations"]  # exact retrieved chunks
    assert trace["citations"][0]["chunk_id"]
    assert trace["citations"][0]["score"] is not None  # reranker score
