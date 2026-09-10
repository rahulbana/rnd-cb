#!/usr/bin/env bash
#
# start.sh — launch the AI SQL Generator (backend + frontend) for development.
#
# Starts the FastAPI backend (uvicorn on :8000) and the Vite dev server
# (:5173). Both run until you press Ctrl-C, which stops them together.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "ERROR: backend/.venv not found. Run ./setup.sh first." >&2
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "ERROR: frontend/node_modules not found. Run ./setup.sh first." >&2
  exit 1
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

# --- Backend --------------------------------------------------------------
echo "==> Starting backend on http://127.0.0.1:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
) &
pids+=("$!")

# --- Frontend -------------------------------------------------------------
echo "==> Starting frontend on http://127.0.0.1:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  exec npm run dev -- --port "$FRONTEND_PORT"
) &
pids+=("$!")

echo ""
echo "==> AI SQL Generator is running:"
echo "      Frontend  →  http://localhost:$FRONTEND_PORT"
echo "      Backend   →  http://localhost:$BACKEND_PORT/api/health"
echo "      API docs  →  http://localhost:$BACKEND_PORT/docs"
echo "    Press Ctrl-C to stop."
echo ""

wait
