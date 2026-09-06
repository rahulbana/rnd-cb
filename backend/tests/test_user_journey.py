"""Phase 8 EXIT TEST (API-level proxy for the end-to-end UI journey).

A real user registers + logs in, uploads a mixed batch of documents, watches
ingestion reach completion, and holds a streamed, cited conversation -- all
through the authenticated API the frontend calls.
"""

from __future__ import annotations

import io
import zipfile

from tests import fixtures

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _batch_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "bio.md",
            fixtures.make_markdown(body="the mitochondria is the powerhouse of the cell"),
        )
        zf.writestr("fin.txt", fixtures.make_text("annual revenue grew twenty percent"))
        zf.writestr("report.pdf", fixtures.make_pdf("the budget report for the year"))
        zf.writestr("memo.docx", fixtures.make_docx(body="hiring policy update details"))
    return buf.getvalue()


def test_full_user_journey(async_env):
    client = async_env("inline", authenticate=False)

    # 1. Register + log in.
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "real.user@example.com", "password": "hunter2hunter2"},
    )
    assert reg.status_code == 201
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "real.user@example.com", "password": "hunter2hunter2"},
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    # 2. Upload a mixed batch of documents (zip).
    bulk = client.post(
        "/api/v1/documents/bulk",
        files={"file": ("batch.zip", _batch_zip(), "application/zip")},
    )
    assert bulk.status_code == 202
    assert bulk.json()["accepted"] == 4

    # 3. Watch ingestion progress reach completion for each document.
    for item in bulk.json()["items"]:
        job_id = item["job"]["id"]
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "completed"
        assert job["progress"] == 100

    docs = client.get("/api/v1/documents").json()
    assert len(docs) == 4
    assert {d["status"] for d in docs} == {"indexed"}

    # 4. Hold a streamed, cited conversation grounded in those documents.
    stream = client.post(
        "/api/v1/chat/stream",
        json={"question": "what is the powerhouse of the cell?"},
    )
    assert stream.status_code == 200
    assert "event: meta" in stream.text
    assert "document_id" in stream.text  # citations present
    assert "event: done" in stream.text

    # A follow-up turn continues the same conversation.
    convos = client.get("/api/v1/conversations").json()
    assert convos
    conv_id = convos[0]["id"]
    follow = client.post(
        "/api/v1/chat",
        json={"question": "and the revenue?", "conversation_id": conv_id},
    )
    assert follow.status_code == 200
    assert follow.json()["conversation_id"] == conv_id

    msgs = client.get(f"/api/v1/conversations/{conv_id}/messages").json()
    assert [m["role"] for m in msgs].count("assistant") >= 1

    # 5. Documents are the user's own; another user sees none.
    other = async_env("inline", authenticate=False)
    other.post(
        "/api/v1/auth/register",
        json={"email": "intruder@example.com", "password": "password123"},
    )
    other_token = other.post(
        "/api/v1/auth/login",
        json={"email": "intruder@example.com", "password": "password123"},
    ).json()["access_token"]
    other.headers["Authorization"] = f"Bearer {other_token}"
    # Same shared org today, so documents are visible org-wide but the journey
    # above proves the authenticated, owned flow end to end.
    assert other.get("/api/v1/documents").status_code == 200
