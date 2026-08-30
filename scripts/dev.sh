#!/usr/bin/env bash
# Local development helper: sets up a venv, installs deps and runs the app.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r backend/requirements.txt

echo "Starting TravelPlanner on http://127.0.0.1:8000 (offline mode unless OPENAI_API_KEY is set)"
cd backend
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
