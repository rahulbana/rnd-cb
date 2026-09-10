#!/usr/bin/env bash
# One-time setup: create the Python virtualenv, install backend deps, install
# frontend deps, and scaffold the backend .env file.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> Setting up the backend (Python / FastAPI)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required but was not found on PATH." >&2
  exit 1
fi

python3 -m venv backend/.venv
# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
deactivate

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "==> Created backend/.env — add your OPENAI_API_KEY to it."
else
  echo "==> backend/.env already exists, leaving it untouched."
fi

echo "==> Setting up the frontend (React / Vite)"
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm (Node.js) is required but was not found on PATH." >&2
  exit 1
fi
(cd frontend && npm install)

echo ""
echo "Setup complete."
echo "Next steps:"
echo "  1. Add your OpenAI key to backend/.env"
echo "  2. Run ./start.sh"
