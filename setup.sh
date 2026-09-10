#!/usr/bin/env bash
# Sets up the AI Meeting Notes Generator: Python virtual env + backend deps + frontend deps.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3.12}"

echo "==> Using $("$PYTHON" --version)"

# --- Backend: virtual environment + dependencies ---
echo "==> Creating virtual environment at backend/.venv"
"$PYTHON" -m venv backend/.venv

# shellcheck disable=SC1091
source backend/.venv/bin/activate

echo "==> Upgrading pip and installing backend dependencies"
pip install --upgrade pip
pip install -r backend/requirements.txt
deactivate

# --- Backend: .env bootstrap ---
if [ ! -f backend/.env ]; then
  echo "==> Creating backend/.env from template (remember to add your OPENAI_API_KEY)"
  cp backend/.env.example backend/.env
fi

# --- Frontend dependencies ---
echo "==> Installing frontend dependencies"
cd frontend
npm install
cd "$ROOT_DIR"

echo ""
echo "Setup complete."
echo "  1. Add your OpenAI API key to backend/.env"
echo "  2. Run ./start.sh to launch the app"
