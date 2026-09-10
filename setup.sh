#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI JSON Generator.
#
#   * Creates a Python 3.12 virtual environment in backend/.venv
#   * Installs Python backend dependencies
#   * Installs React frontend dependencies (npm)
#   * Seeds backend/.env from the example if it doesn't exist
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

echo "==> AI JSON Generator setup"

# --- Locate Python 3.12 -----------------------------------------------------
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON="python3.12"
else
  echo "ERROR: python3.12 was not found on your PATH." >&2
  echo "Please install Python 3.12 and re-run ./setup.sh" >&2
  exit 1
fi

echo "==> Using $($PYTHON --version)"

# --- Create the virtual environment ----------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating virtual environment at backend/.venv"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "==> Reusing existing virtual environment at backend/.venv"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
python -m pip install -r "$BACKEND_DIR/requirements.txt"

deactivate

# --- Seed .env --------------------------------------------------------------
if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "==> Creating backend/.env from .env.example"
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "    -> Edit backend/.env and set your OPENAI_API_KEY"
fi

# --- Install frontend deps --------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies (npm install)"
  (cd "$FRONTEND_DIR" && npm install)
else
  echo "WARNING: npm not found; skipping frontend install." >&2
  echo "         Install Node.js 18+ and run 'npm install' in frontend/." >&2
fi

echo ""
echo "==> Setup complete!"
echo "    1. Add your OpenAI API key to backend/.env"
echo "    2. Run ./start.sh to launch the backend and frontend"
