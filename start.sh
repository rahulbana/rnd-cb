#!/usr/bin/env bash
# Start the FastAPI backend and the Vite frontend together. Ctrl-C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d backend/.venv ]; then
  echo "ERROR: backend/.venv not found. Run ./setup.sh first." >&2
  exit 1
fi
if [ ! -d frontend/node_modules ]; then
  echo "ERROR: frontend/node_modules not found. Run ./setup.sh first." >&2
  exit 1
fi

cleanup() {
  echo ""
  echo "==> Shutting down…"
  # Kill the whole process group of each child if they are still alive.
  [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting backend on http://localhost:8000"
(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "==> Starting frontend on http://localhost:5173"
(
  cd frontend
  exec npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "Both servers are starting. Open http://localhost:5173 in your browser."
echo "Press Ctrl-C to stop."

# Wait for the background servers. `wait -n` (exit as soon as either one dies)
# needs bash 4.3+, so fall back to plain `wait` on older shells (e.g. the
# bash 3.2 that ships with macOS). Either way, Ctrl-C fires the cleanup trap.
if wait -n 2>/dev/null; then
  :
else
  wait
fi
