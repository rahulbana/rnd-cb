#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI SQL Generator.
#
# Creates a Python 3.12 virtual environment for the backend, installs backend
# dependencies, installs frontend node modules, and prepares the .env file.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# --- Python: require 3.12 -------------------------------------------------
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN not found. Please install Python 3.12." >&2
  echo "       (Override with: PYTHON_BIN=/path/to/python3.12 ./setup.sh)" >&2
  exit 1
fi

echo "==> Using $("$PYTHON_BIN" --version)"

# --- Backend: virtual env + deps -----------------------------------------
echo "==> Creating virtual environment at backend/.venv"
"$PYTHON_BIN" -m venv "$BACKEND_DIR/.venv"

# shellcheck disable=SC1091
source "$BACKEND_DIR/.venv/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
pip install -r "$BACKEND_DIR/requirements.txt"

deactivate

# --- Backend: .env --------------------------------------------------------
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "==> Created backend/.env from .env.example"
  echo "    ! Edit backend/.env and set OPENAI_API_KEY before generating SQL."
else
  echo "==> backend/.env already exists — leaving it untouched"
fi

# --- Frontend: node modules ----------------------------------------------
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Please install Node.js 18+ (20/22 recommended)." >&2
  exit 1
fi

echo "==> Installing frontend dependencies (npm install)"
( cd "$FRONTEND_DIR" && npm install )

echo ""
echo "==> Setup complete."
echo "    1. Add your OpenAI key to backend/.env (OPENAI_API_KEY=...)"
echo "    2. Run ./start.sh to launch the backend and frontend."
