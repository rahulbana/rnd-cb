"""Native desktop application built on :mod:`pywebview`.

This wraps the exact same HTML/JS UI and Flask backend used by the web app in
a native OS window, so nothing about the editor experience is re-implemented.
On top of the shared UI it adds the things that only make sense on the desktop:

* a **native window** (no browser, no visible localhost URL)
* native **Open / Save / Save As** file dialogs that read and write real files
  anywhere on disk (not just the managed workspace)
* a native **application menu** (File / Edit / View / Help)

The :class:`DesktopApi` object is exposed to the frontend as
``window.pywebview.api``; the JavaScript detects that bridge and switches from
the browser's file-input / workspace flow to true filesystem access.

Requires a webview backend for your platform (see ``README``):
Windows uses EdgeChromium, macOS uses WKWebView, Linux uses GTK+WebKit2 or Qt.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import webview
from webview.menu import Menu, MenuAction, MenuSeparator

from . import __version__, renderer
from .app import create_app
from .storage import Workspace, default_workspace_dir

_MD_FILETYPES = (
    "Markdown files (*.md;*.markdown;*.mdown;*.mkd;*.txt)",
    "All files (*.*)",
)
_MD_EXTS = (".md", ".markdown", ".mdown", ".mkd", ".txt")


class DesktopApi:
    """Python methods callable from JavaScript via ``window.pywebview.api``.

    All methods return plain JSON-serialisable dicts (or ``None`` when the user
    cancels a dialog) so they cross the JS bridge cleanly.
    """

    def __init__(self) -> None:
        self._window: Optional[webview.Window] = None

    def attach(self, window: "webview.Window") -> None:
        self._window = window

    # -- capability probe -------------------------------------------------

    def is_desktop(self) -> bool:
        return True

    def app_info(self) -> dict:
        return {"version": __version__, "platform": sys.platform}

    # -- file dialogs -----------------------------------------------------

    def open_dialog(self) -> Optional[dict]:
        """Show a native Open dialog and return the chosen file's contents."""
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=_MD_FILETYPES,
        )
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        return self.read_path(path)

    def save_dialog(self, content: str, suggested: str = "Untitled") -> Optional[dict]:
        """Show a native Save dialog, write *content*, and return the path."""
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=self._with_ext(suggested),
            file_types=_MD_FILETYPES,
        )
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        return self.write_path(path, content)

    # -- direct filesystem access ----------------------------------------

    def read_path(self, path: str) -> dict:
        p = Path(path)
        return {"path": str(p), "name": p.stem, "content": p.read_text(encoding="utf-8")}

    def write_path(self, path: str, content: str) -> dict:
        """Write *content* to *path* (adding a ``.md`` extension if missing)."""
        p = Path(self._with_ext(path))
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "name": p.stem}

    def export_html(self, text: str, title: str = "Document") -> Optional[dict]:
        """Render *text* to standalone HTML and save it via a native dialog."""
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=f"{_safe_stem(title)}.html",
            file_types=("HTML files (*.html;*.htm)", "All files (*.*)"),
        )
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        if not path.lower().endswith((".html", ".htm")):
            path += ".html"
        Path(path).write_text(renderer.render_document(text, title=title), encoding="utf-8")
        return {"path": path}

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _with_ext(name: str) -> str:
        return name if name.lower().endswith(_MD_EXTS) else f"{name}.md"


def _safe_stem(title: str) -> str:
    keep = "-_() "
    cleaned = "".join(c for c in title if c.isalnum() or c in keep).strip()
    return cleaned or "document"


# ---------------------------------------------------------------------------
#  Menu wiring
# ---------------------------------------------------------------------------
def _js(window: "webview.Window", fn: str) -> None:
    """Invoke a frontend MDEditor.* action, ignoring pre-load races."""
    window.evaluate_js(f"window.MDEditor && window.MDEditor.{fn}")


def build_menu(window: "webview.Window") -> list:
    """Construct the native application menu bound to frontend actions."""
    return [
        Menu(
            "File",
            [
                MenuAction("New", lambda: _js(window, "newDoc()")),
                MenuAction("Open…", lambda: _js(window, "openFile()")),
                MenuSeparator(),
                MenuAction("Save", lambda: _js(window, "save()")),
                MenuAction("Save As…", lambda: _js(window, "saveAs()")),
                MenuSeparator(),
                MenuAction("Export as HTML…", lambda: _js(window, "exportHtml()")),
                MenuAction("Export as Markdown…", lambda: _js(window, "exportMarkdown()")),
                MenuAction("Print / PDF…", lambda: _js(window, "printDoc()")),
            ],
        ),
        Menu(
            "Edit",
            [
                MenuAction("Bold", lambda: _js(window, "cmd('bold')")),
                MenuAction("Italic", lambda: _js(window, "cmd('italic')")),
                MenuAction("Inline code", lambda: _js(window, "cmd('code')")),
                MenuSeparator(),
                MenuAction("Find & Replace", lambda: _js(window, "find()")),
            ],
        ),
        Menu(
            "View",
            [
                MenuAction("Editor only", lambda: _js(window, "setView('edit')")),
                MenuAction("Split", lambda: _js(window, "setView('split')")),
                MenuAction("Preview only", lambda: _js(window, "setView('preview')")),
                MenuSeparator(),
                MenuAction("Toggle theme", lambda: _js(window, "toggleTheme()")),
                MenuAction("Toggle sidebar", lambda: _js(window, "toggleSidebar()")),
            ],
        ),
        Menu(
            "Help",
            [
                MenuAction("About", lambda: _about(window)),
            ],
        ),
    ]


def _about(window: "webview.Window") -> None:
    window.evaluate_js(
        "window.MDEditor && window.MDEditor.about "
        f"&& window.MDEditor.about('{__version__}')"
    )


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------
def run(
    *,
    workspace: Optional[Path] = None,
    debug: bool = False,
    width: int = 1200,
    height: int = 800,
) -> None:
    """Launch the desktop application window."""
    ws = Workspace(workspace or default_workspace_dir())
    flask_app = create_app(ws)

    api = DesktopApi()
    window = webview.create_window(
        f"Markdown Editor {__version__}",
        flask_app,               # pywebview serves the Flask app internally
        js_api=api,
        width=width,
        height=height,
        min_size=(720, 480),
        confirm_close=True,
        text_select=True,
    )
    api.attach(window)

    webview.start(menu=build_menu(window), debug=debug)


def main(argv: Optional[list] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="markdown-editor-desktop",
        description="Markdown Editor — native desktop app.",
    )
    parser.add_argument("--workspace", type=Path, default=None, help="Document workspace directory")
    parser.add_argument("--debug", action="store_true", help="Open the webview devtools")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    run(workspace=args.workspace, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
