# 📝 Markdown Editor

A **full-featured Markdown editor** with a Python backend that runs both as a
**native desktop app** and as a **web app**. It renders Markdown to HTML in
Python with `python-markdown` + Pygments, and serves a fast, dependency-free
single-page UI with a live split preview, document workspace, toolbar,
keyboard shortcuts, find & replace, and export.

The desktop build wraps the same UI in a native OS window (via
[`pywebview`](https://pywebview.flowrl.com/)) and adds native **Open / Save /
Save As** dialogs and an application menu — see [Desktop app](#desktop-app).

![Split view with live preview, line numbers, syntax highlighting, and an outline sidebar.](docs/screenshot-dark.png)

## Features

**Editing**
- Live, debounced preview rendered by Python (GitHub-flavoured Markdown)
- Formatting toolbar (bold, italic, strikethrough, code, headings, lists,
  task lists, quotes, links, images, tables, code blocks, horizontal rules)
- Keyboard shortcuts: `Ctrl+B`/`I`/`K`/`` ` ``, `Ctrl+O` (open),
  `Ctrl+S` (save), `Ctrl+Shift+S` (save as), `Ctrl+F`, `Ctrl+G`,
  `Ctrl+Alt+N` (new), `Ctrl+Alt+T` (theme), `Ctrl+\` (sidebar)
- Smart editor: line numbers, auto-continued lists/quotes, Tab/Shift-Tab
  indentation, live cursor position & selection length
- Find & replace with case-sensitivity, regex, and match navigation

**Open & Save**
- **Open** a `.md`/`.markdown`/`.txt` file from your computer (button,
  `Ctrl+O`, or drag-and-drop onto the window)
- **Save** writes the current document to the workspace; a new document
  prompts for a name (re-prompting on invalid names, offering overwrite on
  clashes) and then overwrites in place on subsequent saves
- **Save As…** stores a copy under a new name; **Download .md** saves the
  buffer straight to your computer

**Markdown support**
- Tables, footnotes, definition lists, abbreviations, attribute lists
- Fenced code blocks with **Pygments** syntax highlighting
- Task lists, strikethrough, subscript/superscript, insert/mark
- Admonition ("callout") blocks, smart typography, auto-linking
- Auto-generated header anchors, table of contents, and outline navigation

**Documents & workspace**
- Create, open, rename, delete documents stored as `.md` files
- Autosave, unsaved-changes indicator, and file filter
- Path-safe storage (traversal and unsafe names are rejected)

**Preview & export**
- Split / editor-only / preview-only view modes with a draggable splitter
- Scroll sync between editor and preview
- Light & dark themes (persisted)
- Export to standalone **HTML**, raw **Markdown**, or **PDF** (via print)
- Word / character count and reading-time estimate

## Install

Requires Python 3.9+.

```bash
pip install -r requirements.txt
# or, as a package (adds the `markdown-editor` command):
pip install -e .
```

## Desktop app

Run the editor as a native window (no browser, no visible localhost URL):

```bash
pip install -e ".[desktop]"        # installs pywebview
python -m markdown_editor --desktop # or: markdown-editor-desktop
```

In desktop mode you get:

- a **native window** with a **File / Edit / View / Help** menu bar
- native **Open**, **Save**, and **Save As** dialogs that read and write real
  files **anywhere on disk** (not just the managed workspace)
- native **Export to HTML / Markdown** save dialogs
- the same live preview, toolbar, themes, find & replace, and shortcuts as the
  web app

The window remembers the last file you had open and reopens it on launch.

### Platform backend

`pywebview` renders through your OS's native webview, which must be available:

| OS | Backend | Notes |
| --- | --- | --- |
| Windows | EdgeChromium (WebView2) | Preinstalled on Windows 10/11 |
| macOS | WKWebView | Built in |
| Linux | GTK + WebKit2GTK, or Qt WebEngine | e.g. `sudo apt install python3-gi gir1.2-webkit2-4.1` (GTK) or `pip install pyqt5 pyqtwebengine` (Qt) |

## Run (web app)

```bash
python -m markdown_editor          # or: python run.py
```

Then open <http://127.0.0.1:8000/> (a browser opens automatically).

### Options

```
python -m markdown_editor --help

  --host HOST         interface to bind (default: 127.0.0.1)
  --port PORT         port to listen on (default: 8000)
  --workspace DIR     where documents are stored
                      (default: $MDEDITOR_WORKSPACE or ~/markdown-editor-docs)
  --no-browser        do not open a browser on start
  --desktop           launch as a native desktop window (needs pywebview)
  --debug             run Flask in debug mode
```

Documents are stored as plain `.md` files in the workspace directory, so they
remain readable and portable outside the app.

## Architecture

```
markdown_editor/
├── app.py            Flask application factory + JSON API
├── renderer.py       Markdown → HTML (preview & standalone export)
├── storage.py        Path-safe .md document workspace (CRUD)
├── desktop.py        Native desktop shell (pywebview) + JS↔Python bridge
├── __main__.py       CLI runner (web + --desktop)
├── templates/        index.html (single-page UI)
└── static/           style.css (themes + Pygments), app.js (controller)
tests/                pytest suite (renderer, storage, HTTP API, desktop bridge)
```

The frontend is intentionally build-step-free vanilla JavaScript. All Markdown
rendering happens in Python, so the preview and the exported HTML are always
identical. The **same UI and backend serve both the web and desktop builds** —
`desktop.py` wraps them in a native window and the frontend detects the
`window.pywebview` bridge to switch Open/Save over to native file dialogs.

### HTTP API

| Method & path | Purpose |
| --- | --- |
| `POST /api/render` | Markdown → preview HTML + stats + TOC |
| `GET /api/documents` | list documents |
| `POST /api/documents` | create a document |
| `GET /api/documents/<name>` | read a document |
| `PUT /api/documents/<name>` | save (overwrite) a document |
| `POST /api/documents/<name>/rename` | rename a document |
| `DELETE /api/documents/<name>` | delete a document |
| `POST /api/export/html` | download standalone HTML |
| `POST /api/export/markdown` | download raw Markdown |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
