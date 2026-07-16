"""End-to-end tests for the Flask HTTP API."""

import pytest

from markdown_editor.app import create_app
from markdown_editor.storage import Workspace


@pytest.fixture
def client(tmp_path):
    app = create_app(Workspace(tmp_path))
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Markdown" in r.data


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_render_endpoint(client):
    r = client.post("/api/render", json={"text": "# Hi"})
    body = r.get_json()
    assert r.status_code == 200
    assert "<h1" in body["html"]
    assert body["word_count"] == 1


def test_render_rejects_non_string(client):
    r = client.post("/api/render", json={"text": 123})
    assert r.status_code == 400


def test_document_crud_flow(client):
    # create
    r = client.post("/api/documents", json={"name": "Doc", "content": "hello"})
    assert r.status_code == 201
    assert r.get_json()["document"]["name"] == "Doc"

    # list
    docs = client.get("/api/documents").get_json()["documents"]
    assert any(d["name"] == "Doc" for d in docs)

    # read
    doc = client.get("/api/documents/Doc").get_json()["document"]
    assert doc["content"] == "hello"

    # save/overwrite
    client.put("/api/documents/Doc", json={"content": "world"})
    assert client.get("/api/documents/Doc").get_json()["document"]["content"] == "world"

    # rename
    r = client.post("/api/documents/Doc/rename", json={"name": "Renamed"})
    assert r.get_json()["document"]["name"] == "Renamed"
    assert client.get("/api/documents/Doc").status_code == 400  # gone

    # delete
    assert client.delete("/api/documents/Renamed").status_code == 200
    assert client.get("/api/documents/Renamed").status_code == 400


def test_create_autogenerates_unique_name(client):
    r1 = client.post("/api/documents", json={"base": "Untitled"})
    r2 = client.post("/api/documents", json={"base": "Untitled"})
    n1 = r1.get_json()["document"]["name"]
    n2 = r2.get_json()["document"]["name"]
    assert n1 != n2


def test_invalid_name_returns_400(client):
    r = client.post("/api/documents", json={"name": "../evil", "content": "x"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_export_html(client):
    r = client.post("/api/export/html", json={"text": "# Title", "title": "T"})
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("text/html")
    assert b"<!DOCTYPE html>" in r.data
    assert "attachment" in r.headers["Content-Disposition"]


def test_export_markdown(client):
    r = client.post("/api/export/markdown", json={"text": "# Title", "title": "T"})
    assert r.status_code == 200
    assert b"# Title" in r.data
