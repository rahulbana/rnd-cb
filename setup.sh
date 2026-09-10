#!/usr/bin/env bash
# Sets up the backend Python 3.12 virtual environment and the frontend deps.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Setting up backend (Python 3.12 virtual environment)"

# Prefer python3.12; fall back to python3 if it is 3.12.
PY_BIN=""
if command -v python3.12 >/dev/null 2>&1; then
  PY_BIN="python3.12"
elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; exit(0 if sys.version_info[:2]==(3,12) else 1)'; then
  PY_BIN="python3"
else
  echo "ERROR: python3.12 is required but was not found on PATH." >&2
  echo "Install Python 3.12 and re-run ./setup.sh" >&2
  exit 1
fi

echo "    Using interpreter: $($PY_BIN --version)"

cd "$ROOT_DIR/backend"
"$PY_BIN" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Create .env from the example if it does not exist yet.
if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
  echo "    Created backend/.env — add your OPENAI_API_KEY to it."
fi

echo "==> Setting up frontend (npm install)"
cd "$ROOT_DIR/frontend"
if command -v npm >/dev/null 2>&1; then
  npm install
else
  echo "WARNING: npm not found. Install Node.js 18+ to run the frontend." >&2
fi

echo ""
echo "Setup complete!"
echo "  1. Add your OpenAI API key to backend/.env"
echo "  2. Run ./start.sh to launch the app"
