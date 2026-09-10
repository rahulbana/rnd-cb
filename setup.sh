#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI Blog Generator.
#
#   * Creates a Python 3.12 virtual environment for the FastAPI backend
#   * Installs backend Python dependencies
#   * Installs frontend Node dependencies
#   * Creates backend/.env from the example if it does not exist
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> AI Blog Generator setup"

# --- 1. Pick Python 3.12 ---------------------------------------------------
PYTHON_BIN=""
for candidate in python3.12 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")"
    if [ "$version" = "3.12" ]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: Python 3.12 was not found on PATH."
  echo "Please install Python 3.12 and re-run ./setup.sh"
  exit 1
fi
echo "==> Using $($PYTHON_BIN --version) ($PYTHON_BIN)"

# --- 2. Backend virtual environment ---------------------------------------
echo "==> Creating virtual environment at backend/.venv"
"$PYTHON_BIN" -m venv backend/.venv

# shellcheck disable=SC1091
source backend/.venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
pip install -r backend/requirements.txt

deactivate

# --- 3. Backend .env -------------------------------------------------------
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "==> Created backend/.env — add your OPENAI_API_KEY to it."
else
  echo "==> backend/.env already exists (leaving it untouched)."
fi

# --- 4. Frontend dependencies ---------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies (npm install)"
  (cd frontend && npm install)
else
  echo "WARNING: npm not found — skipping frontend install."
  echo "         Install Node.js 18+ and run 'cd frontend && npm install'."
fi

echo ""
echo "==> Setup complete!"
echo "    1. Add your OpenAI key to backend/.env (OPENAI_API_KEY=...)"
echo "    2. Run ./start.sh to launch the backend and frontend."
