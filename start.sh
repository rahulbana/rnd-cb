#!/usr/bin/env bash
#
# start.sh — launch the AI JSON Generator backend and frontend together.
#
#   * Backend  (FastAPI + Uvicorn) on http://localhost:8000
#   * Frontend (Vite + React)      on http://localhost:5173
#
# Press Ctrl+C to stop both.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "ERROR: virtual environment not found. Run ./setup.sh first." >&2
  exit 1
fi

# Track child PIDs so we can clean them up on exit.
PIDS=()

cleanup() {
  echo ""
  echo "==> Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Backend ----------------------------------------------------------------
echo "==> Starting backend on http://localhost:8000"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
PIDS+=($!)

# --- Frontend ---------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Starting frontend on http://localhost:5173"
  (
    cd "$FRONTEND_DIR"
    exec npm run dev
  ) &
  PIDS+=($!)
else
  echo "WARNING: npm not found; frontend not started." >&2
fi

echo ""
echo "==> Running. Backend: http://localhost:8000  Frontend: http://localhost:5173"
echo "    API docs: http://localhost:8000/docs"
echo "    Press Ctrl+C to stop."

wait
