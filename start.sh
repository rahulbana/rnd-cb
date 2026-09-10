#!/usr/bin/env bash
#
# start.sh — run the backend (FastAPI/uvicorn) and frontend (Vite) together.
#
# Both processes run concurrently. Press Ctrl+C to stop both cleanly.
#
# Usage:
#   ./start.sh                 # backend on :8000, frontend on :5173
#   BACKEND_PORT=9000 ./start.sh
#   FRONTEND_PORT=3000 ./start.sh
#
# Run ./setup.sh first if you haven't installed dependencies yet.
#
set -euo pipefail

# Enable job control so each backgrounded service becomes its own process
# group leader; we can then signal the whole group (service + its children,
# e.g. uvicorn's reload worker and Vite's esbuild) on shutdown.
set -m

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

# --- preflight checks -------------------------------------------------------
VENV_PY="$BACKEND_DIR/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  error "Backend virtual environment not found at backend/.venv"
  error "Run ./setup.sh first."
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  error "Frontend dependencies not installed (frontend/node_modules missing)."
  error "Run ./setup.sh first."
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  info "Warning: backend/.env not found — the server may fail without OPENAI_API_KEY."
fi

# --- process management -----------------------------------------------------
PIDS=()

cleanup() {
  trap - INT TERM EXIT  # avoid re-entry
  info "Shutting down…"
  for pid in "${PIDS[@]}"; do
    # Negative PID targets the whole process group (service + its children),
    # so uvicorn's reload worker and Vite's subprocesses are stopped too.
    kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  info "Stopped."
}
trap cleanup INT TERM EXIT

# --- start backend ----------------------------------------------------------
info "Starting backend on http://localhost:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  exec "$VENV_PY" -m uvicorn app.main:app --reload --port "$BACKEND_PORT"
) &
PIDS+=("$!")

# --- start frontend ---------------------------------------------------------
info "Starting frontend on http://localhost:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  # Point the dev proxy at the chosen backend port.
  exec env VITE_API_TARGET="http://localhost:$BACKEND_PORT" \
    npm run dev -- --port "$FRONTEND_PORT"
) &
PIDS+=("$!")

info "Both services are running. Press Ctrl+C to stop."

# Wait for either process to exit; if one dies, cleanup (via trap) stops the other.
wait -n
