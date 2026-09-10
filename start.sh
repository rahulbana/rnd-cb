#!/usr/bin/env bash
#
# start.sh — run the AI Resume Analyzer (backend + frontend).
#
# Starts the FastAPI backend (uvicorn) on port 8000 and the Vite dev
# server on port 5173. Ctrl+C stops both.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [ ! -d "$VENV_DIR" ]; then
  echo "ERROR: backend/.venv not found. Run ./setup.sh first." >&2
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "WARNING: backend/.env not found. The API will start but analysis will fail" >&2
  echo "         until OPENAI_API_KEY is set. Run ./setup.sh or create backend/.env." >&2
fi

pids=()
cleanup() {
  echo ""
  echo "==> Shutting down…"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# --- Backend -----------------------------------------------------------------
echo "==> Starting backend on http://localhost:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  exec uvicorn app.main:app --reload --port "$BACKEND_PORT"
) &
pids+=($!)

# --- Frontend ----------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Starting frontend on http://localhost:$FRONTEND_PORT"
  (
    cd "$FRONTEND_DIR"
    exec npm run dev -- --port "$FRONTEND_PORT"
  ) &
  pids+=($!)
else
  echo "WARNING: npm not found — frontend not started." >&2
fi

echo ""
echo "==> Backend:  http://localhost:$BACKEND_PORT/docs"
echo "==> Frontend: http://localhost:$FRONTEND_PORT"
echo "==> Press Ctrl+C to stop."

wait
