#!/usr/bin/env bash
# Set up the AI Question Generator: Python virtualenv + backend deps + frontend deps.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3.12}"

echo "==> Checking for $PYTHON"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON not found. Install Python 3.12 or set PYTHON=<path>." >&2
  exit 1
fi
"$PYTHON" --version

# ---------------------------------------------------------------------------
# Backend: virtualenv + dependencies
# ---------------------------------------------------------------------------
echo "==> Creating virtual environment at .venv"
"$PYTHON" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
pip install -r backend/requirements.txt

# ---------------------------------------------------------------------------
# Backend env file
# ---------------------------------------------------------------------------
if [ ! -f backend/.env ]; then
  echo "==> Creating backend/.env from example (add your OPENAI_API_KEY!)"
  cp backend/.env.example backend/.env
else
  echo "==> backend/.env already exists — leaving it untouched"
fi

# ---------------------------------------------------------------------------
# Frontend: npm dependencies
# ---------------------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies"
  (cd frontend && npm install)
else
  echo "WARNING: npm not found — skipping frontend install. Install Node.js 18+ and run 'cd frontend && npm install'." >&2
fi

echo ""
echo "Setup complete."
echo "  1. Add your OpenAI key to backend/.env (OPENAI_API_KEY=...)"
echo "  2. Run ./start.sh to launch the backend and frontend."
