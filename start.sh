#!/usr/bin/env bash
# Starts the FastAPI backend and the Vite/React frontend together.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d backend/.venv ]; then
  echo "Virtual environment not found. Run ./setup.sh first." >&2
  exit 1
fi

if [ ! -d frontend/node_modules ]; then
  echo "Frontend dependencies not found. Run ./setup.sh first." >&2
  exit 1
fi

# Shut both servers down on Ctrl+C.
pids=()
cleanup() {
  echo ""
  echo "==> Shutting down..."
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "==> Starting backend on http://localhost:8000"
(
  cd backend
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --port 8000
) &
pids+=("$!")

echo "==> Starting frontend on http://localhost:5173"
(
  cd frontend
  exec npm run dev
) &
pids+=("$!")

wait
