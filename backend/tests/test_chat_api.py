"""Chat API: grounded cited answers, streaming, not-found, history."""

from __future__ import annotations

from tests import fixtures


def _ingest(client, name, body):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, fixtures.make_markdown(body=body), "text/markdown")},
    )


def test_chat_grounded_answer_with_citations(upload_client):
    _ingest(upload_client, "bio.md", "the mitochondria is the powerhouse of the cell")
    resp = upload_client.post(
        "/api/v1/chat", json={"question": "what is the powerhouse of the cell"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["citations"]  # grounded -> has citations
    assert body["citations"][0]["document_id"]
    assert body["provider"] == "fake"
    assert body["prompt_version"] == "v1"
    assert body["conversation_id"]


def test_chat_not_found_when_no_context(upload_client):
    # No documents ingested -> nothing to ground on.
    resp = upload_client.post("/api/v1/chat", json={"question": "anything at all"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["citations"] == []


def test_chat_persists_conversation_and_history(upload_client):
    _ingest(upload_client, "d.md", "alpha beta gamma content")
    first = upload_client.post(
        "/api/v1/chat", json={"question": "tell me about alpha"}
    ).json()
    conv_id = first["conversation_id"]
    # Continue the same conversation.
    upload_client.post(
        "/api/v1/chat",
        json={"question": "and beta?", "conversation_id": conv_id},
    )

    msgs = upload_client.get(f"/api/v1/conversations/{conv_id}/messages").json()
    roles = [m["role"] for m in msgs]
    # 2 user + 2 assistant turns.
    assert roles.count("user") == 2
    assert roles.count("assistant") == 2

    convos = upload_client.get("/api/v1/conversations").json()
    assert any(c["id"] == conv_id for c in convos)


def test_chat_stream_sse(upload_client):
    _ingest(upload_client, "s.md", "streaming content about widgets")
    resp = upload_client.post(
        "/api/v1/chat/stream", json={"question": "tell me about widgets"}
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "event: meta" in text
    assert "event: done" in text
    assert "data:" in text


def test_chat_empty_question_400(upload_client):
    assert upload_client.post("/api/v1/chat", json={"question": "  "}).status_code == 400
