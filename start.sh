#!/usr/bin/env bash
#
# start.sh — run the backend (FastAPI) and frontend (Vite) together.
# Ctrl-C stops both.
#
# Usage: ./start.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

if [ ! -x "$VENV_DIR/bin/uvicorn" ]; then
  echo "ERROR: backend not set up. Run ./setup.sh first." >&2
  exit 1
fi

# Track child PIDs so we can clean them up on exit.
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

echo "==> Starting backend on http://localhost:8000"
(
  cd "$BACKEND_DIR"
  exec "$VENV_DIR/bin/uvicorn" app.main:app --reload --port 8000
) &
pids+=($!)

if command -v npm >/dev/null 2>&1 && [ -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> Starting frontend on http://localhost:5173"
  (
    cd "$FRONTEND_DIR"
    exec npm run dev
  ) &
  pids+=($!)
else
  echo "  [!] Frontend deps missing (run ./setup.sh). Backend only."
fi

echo "==> Running. Press Ctrl-C to stop."
wait
