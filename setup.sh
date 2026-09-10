#!/usr/bin/env bash
#
# setup.sh — one-time setup for the AI Text Summarizer.
#   - creates a Python virtualenv and installs backend dependencies
#   - installs frontend dependencies and builds the React app into ./public
#   - seeds .env from .env.example if it doesn't exist yet
#
# Run once after cloning (and again whenever dependencies change).

set -euo pipefail

# Always operate from the repository root (the directory this script lives in).
cd "$(dirname "$0")"

# Python interpreter used for the virtualenv (override with PYTHON=... ./setup.sh).
PYTHON="${PYTHON:-python3.12}"

echo "==> Checking prerequisites"
command -v "$PYTHON" >/dev/null 2>&1 || { echo "ERROR: $PYTHON is required but not found. Install Python 3.12, or run 'PYTHON=python3 ./setup.sh' to use another interpreter." >&2; exit 1; }
command -v npm >/dev/null 2>&1      || { echo "ERROR: npm (Node.js) is required but not found." >&2; exit 1; }

# ---------------------------------------------------------------------------
# Backend: virtualenv + Python dependencies
# ---------------------------------------------------------------------------
if [ ! -d .venv ]; then
  echo "==> Creating virtualenv (.venv) with $($PYTHON --version)"
  "$PYTHON" -m venv .venv
fi

echo "==> Installing Python dependencies"
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Frontend: npm install + production build (outputs to ./public)
# ---------------------------------------------------------------------------
echo "==> Installing frontend dependencies"
( cd frontend && npm install )

echo "==> Building frontend (outputs to ./public)"
( cd frontend && npm run build )

# ---------------------------------------------------------------------------
# Environment file
# ---------------------------------------------------------------------------
if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  echo "    Edit .env and set OPENAI_API_KEY before running ./start.sh"
fi

echo ""
echo "Setup complete. Next:"
echo "  1. Put your OpenAI key in .env (OPENAI_API_KEY=...)"
echo "  2. Run ./start.sh"
