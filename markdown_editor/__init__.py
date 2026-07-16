"""A full-featured, browser-based Markdown editor with a Python backend.

The public entry points are :func:`markdown_editor.app.create_app` for the
Flask application and the :mod:`markdown_editor.__main__` command-line runner.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .app import create_app  # noqa: E402  (re-export for convenience)

__all__ = ["create_app", "__version__"]
