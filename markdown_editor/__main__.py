"""Command-line entry point: ``python -m markdown_editor``.

Starts the local web server and (optionally) opens the editor in a browser.
"""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__
from .app import create_app
from .storage import Workspace, default_workspace_dir


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markdown_editor",
        description="A full-featured, browser-based Markdown editor.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Directory used to store documents (default: $MDEDITOR_WORKSPACE or ~/markdown-editor-docs)",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window on start")
    parser.add_argument("--debug", action="store_true", help="Run Flask in debug mode")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    workspace_dir = args.workspace or default_workspace_dir()
    workspace = Workspace(workspace_dir)
    app = create_app(workspace)

    url = f"http://{args.host}:{args.port}/"
    print(f"Markdown Editor {__version__}")
    print(f"  workspace : {workspace.root}")
    print(f"  serving   : {url}")
    print("  press Ctrl+C to stop")

    if not args.no_browser and not args.debug:
        # Open the browser shortly after the server begins accepting sockets.
        threading.Timer(1.0, lambda: _open_browser(url)).start()

    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:  # pragma: no cover - interactive
        print("\nStopped.")
    return 0


def _open_browser(url: str) -> None:  # pragma: no cover - environment dependent
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
