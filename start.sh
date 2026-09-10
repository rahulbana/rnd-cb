#!/usr/bin/env bash
#
# start.sh — run the backend and frontend together for local development.
#
# Backend:  FastAPI via uvicorn on http://127.0.0.1:8000
# Frontend: Vite dev server on http://127.0.0.1:5173 (proxies /api to backend)
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d backend/.venv ]; then
  echo "ERROR: backend/.venv not found. Run ./setup.sh first." >&2
  exit 1
fi
if [ ! -d frontend/node_modules ]; then
  echo "ERROR: frontend/node_modules not found. Run ./setup.sh first." >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "==> Shutting down…"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting backend on http://127.0.0.1:8000"
(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

echo "==> Starting frontend on http://127.0.0.1:5173"
(
  cd frontend
  exec npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "==> Both servers running."
echo "    Frontend: http://localhost:5173"
echo "    Backend:  http://localhost:8000  (docs at /docs)"
echo "    Press Ctrl+C to stop both."
echo ""

wait
