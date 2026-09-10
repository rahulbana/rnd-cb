#!/usr/bin/env bash
#
# start.sh — run the AI Text Summarizer server.
#   Serves the API and the built React frontend with uvicorn.
#
# Usage:
#   ./start.sh            # run on PORT (from .env, default 3000)
#   ./start.sh --reload   # development mode with auto-reload
#   ./start.sh --port 8080 --reload   # any extra args pass through to uvicorn
#
# Run ./setup.sh first.

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/uvicorn ]; then
  echo "ERROR: virtualenv not found. Run ./setup.sh first." >&2
  exit 1
fi

if [ ! -f public/index.html ]; then
  echo "WARNING: frontend not built (public/index.html missing)." >&2
  echo "         The API will work, but the UI won't. Run ./setup.sh to build it." >&2
fi

# Port: CLI --port wins (passed through in "$@"); otherwise read PORT from .env,
# otherwise default to 3000.
PORT="$(grep -E '^PORT=' .env 2>/dev/null | tail -1 | cut -d= -f2 | tr -d '[:space:]' || true)"
PORT="${PORT:-3000}"

echo "==> Starting server on http://localhost:${PORT}"
exec ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" "$@"
