#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI Resume Analyzer.
#
# Creates a Python 3.12 virtual environment for the FastAPI backend,
# installs backend dependencies, installs frontend dependencies, and
# prepares a .env file for your OpenAI API key.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"

echo "==> AI Resume Analyzer setup"

# --- Check Python 3.12 -------------------------------------------------------
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: '$PYTHON_BIN' not found. Please install Python 3.12." >&2
  echo "       (You can override the interpreter with: PYTHON_BIN=/path/to/python3.12 ./setup.sh)" >&2
  exit 1
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "==> Using Python $PY_VERSION ($PYTHON_BIN)"
if [ "$PY_VERSION" != "3.12" ]; then
  echo "WARNING: Expected Python 3.12 but found $PY_VERSION. Continuing anyway." >&2
fi

# --- Backend: virtual env + deps --------------------------------------------
echo "==> Creating virtual environment at backend/.venv"
"$PYTHON_BIN" -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
python -m pip install -r "$BACKEND_DIR/requirements.txt"

deactivate

# --- Backend: .env -----------------------------------------------------------
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "==> Created backend/.env — add your OPENAI_API_KEY there."
else
  echo "==> backend/.env already exists — leaving it untouched."
fi

# --- Frontend: deps ----------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies (npm install)"
  (cd "$FRONTEND_DIR" && npm install)
else
  echo "WARNING: npm not found — skipping frontend install. Install Node.js 18+ and run 'npm install' in frontend/." >&2
fi

echo ""
echo "==> Setup complete."
echo "    1. Add your OpenAI API key to backend/.env"
echo "    2. Run ./start.sh to launch the app."
