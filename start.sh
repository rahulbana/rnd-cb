#!/usr/bin/env bash
#
# start.sh — launch the AI Code Explainer backend and frontend together.
#
# Starts the FastAPI backend (uvicorn) on :8000 and the Vite dev server on
# :5173. Ctrl-C stops both.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv ]; then
  echo "ERROR: .venv not found. Run ./setup.sh first." >&2
  exit 1
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# shellcheck disable=SC1091
source .venv/bin/activate

# Track child PIDs so we can clean up on exit.
PIDS=()

cleanup() {
  echo ""
  echo "==> Shutting down…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> Starting backend on http://localhost:${BACKEND_PORT}"
(
  cd backend
  exec uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload
) &
PIDS+=($!)

if command -v npm >/dev/null 2>&1 && [ -d frontend/node_modules ]; then
  echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}"
  (
    cd frontend
    exec npm run dev -- --port "$FRONTEND_PORT"
  ) &
  PIDS+=($!)
else
  echo "WARNING: frontend deps not installed — running backend only." >&2
  echo "Run ./setup.sh (or 'cd frontend && npm install') to enable the UI." >&2
fi

echo ""
echo "==> App is starting. Open http://localhost:${FRONTEND_PORT}"
echo "    Press Ctrl-C to stop."

# Wait for any child to exit.
wait
