#!/usr/bin/env bash
# Starts the FastAPI backend and the Vite frontend together.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d "$ROOT_DIR/backend/.venv" ]; then
  echo "ERROR: backend/.venv not found. Run ./setup.sh first." >&2
  exit 1
fi

# Start the backend.
echo "==> Starting backend on http://localhost:8000"
cd "$ROOT_DIR/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
deactivate || true

# Start the frontend.
echo "==> Starting frontend on http://localhost:5173"
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Clean up both processes on exit.
cleanup() {
  echo ""
  echo "==> Shutting down…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "App running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000/docs"
echo "Press Ctrl+C to stop."

wait
