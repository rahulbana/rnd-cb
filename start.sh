#!/usr/bin/env bash
# Launch the FastAPI backend and the Vite frontend together.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv ]; then
  echo "ERROR: .venv not found. Run ./setup.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "==> Starting FastAPI backend on http://$BACKEND_HOST:$BACKEND_PORT"
(cd backend && uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload) &
BACKEND_PID=$!

# Stop the backend when this script exits.
cleanup() {
  echo ""
  echo "==> Shutting down…"
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if command -v npm >/dev/null 2>&1; then
  echo "==> Starting Vite frontend on http://localhost:5173"
  (cd frontend && npm run dev)
else
  echo "WARNING: npm not found — running backend only." >&2
  echo "API docs available at http://$BACKEND_HOST:$BACKEND_PORT/docs"
  wait "$BACKEND_PID"
fi
