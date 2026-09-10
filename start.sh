#!/usr/bin/env bash
#
# Starts the AI Translator backend (FastAPI/uvicorn) and frontend (Vite).
# Both run until you press Ctrl+C, which stops them together.
#
#   Backend:  http://127.0.0.1:8000  (docs at /docs)
#   Frontend: http://localhost:5173
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv ]; then
  echo "ERROR: .venv not found. Run ./setup.sh first." >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "WARNING: .env not found. Copy .env.example to .env and set OPENAI_API_KEY." >&2
fi

# shellcheck disable=SC1091
source .venv/bin/activate

PIDS=()
cleanup() {
  echo ""
  echo "==> Shutting down…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> Starting backend on http://127.0.0.1:8000"
(cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
PIDS+=($!)

if command -v npm >/dev/null 2>&1 && [ -d frontend/node_modules ]; then
  echo "==> Starting frontend on http://localhost:5173"
  (cd frontend && npm run dev) &
  PIDS+=($!)
else
  echo "WARNING: frontend not started (npm or node_modules missing). Run ./setup.sh." >&2
fi

echo ""
echo "AI Translator is running. Press Ctrl+C to stop."
wait
