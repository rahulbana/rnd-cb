#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI Resume/CV Generator.
#
#   * Creates a Python 3.12 virtual environment in backend/.venv
#   * Installs backend (FastAPI/OpenAI/WeasyPrint) dependencies
#   * Installs frontend (React/Vite) dependencies
#   * Creates backend/.env from the example if it doesn't exist
#
# Usage: ./setup.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

# Prefer python3.12 explicitly (as requested), fall back to python3.
PYTHON_BIN="$(command -v python3.12 || command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: python3.12 (or python3) not found on PATH." >&2
  exit 1
fi

echo "==> Using Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

# ---------------------------------------------------------------------------
# WeasyPrint native dependency note.
# WeasyPrint needs Pango/Cairo/GDK-PixBuf shared libraries to render PDFs.
# We don't install them automatically (needs sudo), but we detect and warn.
# ---------------------------------------------------------------------------
if ! ldconfig -p 2>/dev/null | grep -qi 'libpango-1.0'; then
  cat <<'NOTE'

  [!] WeasyPrint system libraries appear to be missing. PDF export needs them.
      Install (Debian/Ubuntu):
        sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 \
             libgdk-pixbuf-2.0-0 libffi-dev libcairo2
      macOS (Homebrew):
        brew install pango cairo gdk-pixbuf libffi
      The app still runs and previews without these; only PDF download needs them.

NOTE
fi

# ---------------------------------------------------------------------------
# Backend: virtual environment + dependencies
# ---------------------------------------------------------------------------
echo "==> Creating virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

echo "==> Installing backend dependencies"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# Backend: .env
# ---------------------------------------------------------------------------
if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "==> Creating backend/.env from .env.example"
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "    (Add your OPENAI_API_KEY to backend/.env to enable AI rewriting.)"
fi

# ---------------------------------------------------------------------------
# Frontend: npm install
# ---------------------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies"
  (cd "$FRONTEND_DIR" && npm install)
else
  echo "  [!] npm not found — skipping frontend install. Install Node 18+ and run 'npm install' in frontend/."
fi

cat <<'DONE'

==> Setup complete.

Next:
  1. (Optional) Add your OpenAI key to backend/.env
  2. Start everything:   ./start.sh

Backend runs on http://localhost:8000  (API docs at /docs)
Frontend runs on http://localhost:5173

DONE
