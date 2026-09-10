#!/usr/bin/env bash
#
# setup.sh — one-time setup for AI Code Explainer.
#
# Creates a Python 3.12 virtual environment, installs backend dependencies,
# installs frontend dependencies, and prepares backend/.env.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# --- Pick Python 3.12 -------------------------------------------------------
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
  echo "Install Python 3.12 and re-run ./setup.sh" >&2
  exit 1
fi

echo "==> Using $("$PYTHON_BIN" --version) ($PYTHON_BIN)"

# --- Backend virtual environment -------------------------------------------
echo "==> Creating virtual environment at .venv"
"$PYTHON_BIN" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing backend dependencies"
pip install -r backend/requirements.txt

# --- Backend env file -------------------------------------------------------
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "==> Created backend/.env (add your OPENAI_API_KEY to it)"
else
  echo "==> backend/.env already exists — leaving it unchanged"
fi

deactivate

# --- Frontend dependencies --------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies (npm install)"
  (cd frontend && npm install)
else
  echo "WARNING: npm not found — skipping frontend install." >&2
  echo "Install Node.js (18+) and run 'cd frontend && npm install'." >&2
fi

echo ""
echo "==> Setup complete!"
echo "    1. Add your OpenAI key to backend/.env"
echo "    2. Run ./start.sh to launch the app"
