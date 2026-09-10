#!/usr/bin/env bash
#
# One-time setup for the AI Translator app.
#   - Creates a Python 3.12 virtual environment in ./.venv
#   - Installs backend dependencies
#   - Installs frontend (npm) dependencies
#   - Creates a .env file from .env.example if one does not exist
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# --- Pick Python 3.12 ---------------------------------------------------------
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
  echo "ERROR: Python 3.12 is required but was not found on PATH." >&2
  echo "Install Python 3.12 (e.g. 'sudo apt install python3.12 python3.12-venv') and re-run." >&2
  exit 1
fi

echo "==> Using $("$PYTHON_BIN" --version) ($PYTHON_BIN)"

# --- Backend virtual environment ---------------------------------------------
echo "==> Creating virtual environment in .venv"
"$PYTHON_BIN" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
python -m pip install -r backend/requirements.txt

deactivate

# --- Frontend dependencies ---------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies (npm install)"
  (cd frontend && npm install)
else
  echo "WARNING: npm not found. Skipping frontend install." >&2
  echo "         Install Node.js 18+ and run 'cd frontend && npm install'." >&2
fi

# --- .env --------------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — add your OPENAI_API_KEY before running."
else
  echo "==> .env already exists, leaving it untouched."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit .env and set OPENAI_API_KEY"
echo "  2. Run ./start.sh"
