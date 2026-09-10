#!/usr/bin/env bash
#
# start.sh — run the backend (FastAPI/uvicorn) and frontend (Vite) together.
#
# Both processes run in the foreground; Ctrl-C stops both.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [ ! -d backend/.venv ]; then
  echo "Error: backend/.venv not found. Run ./setup.sh first." >&2
  exit 1
fi

if [ ! -f backend/.env ]; then
  echo "Warning: backend/.env not found. Transformations will fail until" >&2
  echo "         OPENAI_API_KEY is set. Run ./setup.sh or create it." >&2
fi

# --- Cleanup: kill child processes on exit ----------------------------------
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

# --- Backend ----------------------------------------------------------------
echo "==> Starting backend on http://127.0.0.1:${BACKEND_PORT}"
(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload
) &
pids+=("$!")

# --- Frontend ---------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}"
  (
    cd frontend
    exec npm run dev -- --port "$FRONTEND_PORT"
  ) &
  pids+=("$!")
else
  echo "Warning: npm not found — frontend not started." >&2
fi

echo ""
echo "App running:"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo "  Backend:  http://127.0.0.1:${BACKEND_PORT}/api/health"
echo "  Docs:     http://127.0.0.1:${BACKEND_PORT}/docs"
echo "Press Ctrl-C to stop."

wait
