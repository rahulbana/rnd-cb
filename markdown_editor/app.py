"""Flask application factory and HTTP API for the markdown editor.

Routes
------
UI
    ``GET  /``                      the editor single-page app

Rendering
    ``POST /api/render``            markdown -> preview HTML + metadata

Documents (workspace CRUD)
    ``GET    /api/documents``           list documents
    ``POST   /api/documents``           create a document
    ``GET    /api/documents/<name>``    read a document
    ``PUT    /api/documents/<name>``    save (overwrite) a document
    ``POST   /api/documents/<name>/rename``  rename a document
    ``DELETE /api/documents/<name>``    delete a document

Export
    ``POST /api/export/html``       download a standalone HTML page
    ``POST /api/export/markdown``   download the raw markdown

The API is JSON in / JSON out (except downloads).  Errors are returned as
``{"error": "..."}`` with an appropriate 4xx/5xx status.
"""

from __future__ import annotations

import io
from typing import Optional

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
)

from . import renderer
from .storage import StorageError, Workspace, default_workspace_dir


def create_app(workspace: Optional[Workspace] = None) -> Flask:
    """Build and configure the Flask application.

    Passing an explicit *workspace* makes the app trivially testable against a
    temporary directory.
    """
    app = Flask(__name__)
    app.config["WORKSPACE"] = workspace or Workspace(default_workspace_dir())
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB safety cap

    def ws() -> Workspace:
        return app.config["WORKSPACE"]

    # -- error handling ---------------------------------------------------

    @app.errorhandler(StorageError)
    def _handle_storage_error(exc: StorageError):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(413)
    def _handle_too_large(_exc):
        return jsonify(error="Document is too large."), 413

    def _json_body() -> dict:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    # -- UI ---------------------------------------------------------------

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # -- rendering --------------------------------------------------------

    @app.post("/api/render")
    def api_render():
        text = _json_body().get("text", "")
        if not isinstance(text, str):
            return jsonify(error="'text' must be a string."), 400
        result = renderer.render(text)
        return jsonify(
            html=result.html,
            toc=result.toc,
            toc_tokens=result.toc_tokens,
            word_count=result.word_count,
            char_count=result.char_count,
            reading_minutes=result.reading_minutes,
        )

    # -- documents --------------------------------------------------------

    @app.get("/api/documents")
    def api_list_documents():
        docs = [info.to_dict() for info in ws().list_documents()]
        return jsonify(documents=docs)

    @app.post("/api/documents")
    def api_create_document():
        body = _json_body()
        name = body.get("name") or ws().unique_name(body.get("base", "Untitled"))
        content = body.get("content", "")
        if not isinstance(content, str):
            return jsonify(error="'content' must be a string."), 400
        doc = ws().create(name, content)
        return jsonify(document=doc.to_dict()), 201

    @app.get("/api/documents/<path:name>")
    def api_read_document(name: str):
        doc = ws().read(name)
        return jsonify(document=doc.to_dict())

    @app.put("/api/documents/<path:name>")
    def api_save_document(name: str):
        body = _json_body()
        content = body.get("content", "")
        if not isinstance(content, str):
            return jsonify(error="'content' must be a string."), 400
        doc = ws().write(name, content)
        return jsonify(document=doc.to_dict())

    @app.post("/api/documents/<path:name>/rename")
    def api_rename_document(name: str):
        new_name = _json_body().get("name", "")
        doc = ws().rename(name, new_name)
        return jsonify(document=doc.to_dict())

    @app.delete("/api/documents/<path:name>")
    def api_delete_document(name: str):
        ws().delete(name)
        return jsonify(deleted=name)

    # -- export -----------------------------------------------------------

    @app.post("/api/export/html")
    def api_export_html():
        body = _json_body()
        text = body.get("text", "")
        title = body.get("title", "Document") or "Document"
        html = renderer.render_document(text, title=title)
        return _download(html, f"{_safe_filename(title)}.html", "text/html")

    @app.post("/api/export/markdown")
    def api_export_markdown():
        body = _json_body()
        text = body.get("text", "")
        title = body.get("title", "Document") or "Document"
        return _download(text, f"{_safe_filename(title)}.md", "text/markdown")

    return app


def _download(text: str, filename: str, mimetype: str) -> Response:
    buffer = io.BytesIO(text.encode("utf-8"))
    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


def _safe_filename(title: str) -> str:
    keep = "-_() "
    cleaned = "".join(c for c in title if c.isalnum() or c in keep).strip()
    return cleaned or "document"
