#!/usr/bin/env bash
# Convenience script to run backend + frontend together for local development.
# Usage: ./dev.sh   (Ctrl-C stops both)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Backend ---
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f .env ]; then
  echo "⚠️  backend/.env not found — copy .env.example and set OPENAI_API_KEY"
fi
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# --- Frontend ---
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM
wait
