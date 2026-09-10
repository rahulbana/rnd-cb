#!/usr/bin/env bash
#
# start.sh — launch the FastAPI backend and the React (Vite) frontend together.
#
# Backend:  http://localhost:8000  (API + docs at /docs)
# Frontend: http://localhost:5173
#
# Press Ctrl+C to stop both.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d backend/.venv ]; then
  echo "ERROR: backend/.venv not found. Run ./setup.sh first."
  exit 1
fi

if [ ! -f backend/.env ]; then
  echo "WARNING: backend/.env not found — the backend will start but generation"
  echo "         will fail until you add OPENAI_API_KEY. See backend/.env.example."
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

# --- Backend ---------------------------------------------------------------
echo "==> Starting backend on http://localhost:8000"
(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
pids+=($!)

# --- Frontend --------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  echo "==> Starting frontend on http://localhost:5173"
  (
    cd frontend
    exec npm run dev
  ) &
  pids+=($!)
else
  echo "WARNING: npm not found — frontend not started."
fi

echo ""
echo "==> Backend:  http://localhost:8000/docs"
echo "==> Frontend: http://localhost:5173"
echo "==> Press Ctrl+C to stop."

wait
