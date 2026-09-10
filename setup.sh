#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI Grammar & Rewriting Assistant.
#
# Creates a Python 3.12 virtual environment for the FastAPI backend,
# installs backend + frontend dependencies, and prepares backend/.env.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# --- Pick a Python 3.12 interpreter -----------------------------------------
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: '$PYTHON_BIN' not found. Install Python 3.12 or set PYTHON_BIN." >&2
  exit 1
fi

echo "==> Using $($PYTHON_BIN --version)"

# --- Backend: virtual environment -------------------------------------------
echo "==> Creating virtual environment at backend/.venv"
"$PYTHON_BIN" -m venv backend/.venv

# shellcheck disable=SC1091
source backend/.venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --quiet --upgrade pip

echo "==> Installing backend dependencies"
python -m pip install --quiet -r backend/requirements.txt

deactivate

# --- Backend: .env -----------------------------------------------------------
if [ ! -f backend/.env ]; then
  echo "==> Creating backend/.env from template"
  cp backend/.env.example backend/.env
  echo "    Edit backend/.env and set OPENAI_API_KEY before running."
else
  echo "==> backend/.env already exists — leaving it untouched"
fi

# --- Frontend: npm install ---------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies (npm install)"
  (cd frontend && npm install --silent)
else
  echo "Warning: npm not found — skipping frontend install." >&2
fi

echo ""
echo "Setup complete."
echo "  1. Add your key to backend/.env  (OPENAI_API_KEY=...)"
echo "  2. Run ./start.sh"
