#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI Sentiment Analyzer.
#
# Creates a Python 3.12 virtual environment for the FastAPI backend,
# installs backend + frontend dependencies, and prepares the .env file.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"

echo "==> AI Sentiment Analyzer :: setup"

# --- Checks --------------------------------------------------------------
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: '$PYTHON_BIN' not found. Install Python 3.12 or set PYTHON_BIN." >&2
  exit 1
fi
echo "==> Using $("$PYTHON_BIN" --version)"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: 'npm' not found. Install Node.js (18+) to build the frontend." >&2
  exit 1
fi
echo "==> Using node $(node --version), npm $(npm --version)"

# --- Backend: virtual environment ---------------------------------------
echo "==> Creating Python virtual environment at ./backend/.venv"
"$PYTHON_BIN" -m venv backend/.venv

# shellcheck disable=SC1091
source backend/.venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
pip install -r backend/requirements.txt

deactivate

# --- Backend: environment file ------------------------------------------
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "==> Created backend/.env from template."
  echo "    Add your OPENAI_API_KEY to backend/.env to enable OpenAI-powered analysis."
  echo "    (Without a key the app runs with a lexicon-based fallback engine.)"
else
  echo "==> backend/.env already exists, leaving it untouched."
fi

# --- Frontend ------------------------------------------------------------
echo "==> Installing frontend dependencies"
( cd frontend && npm install )

echo ""
echo "==> Setup complete!"
echo "    Run ./start.sh to launch the backend (:8000) and frontend (:5173)."
