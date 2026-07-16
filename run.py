#!/usr/bin/env python3
"""Convenience launcher: ``python run.py`` starts the editor.

Equivalent to ``python -m markdown_editor``.  Accepts the same arguments
(``--host``, ``--port``, ``--workspace``, ``--no-browser``, ``--debug``).
"""

from markdown_editor.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
