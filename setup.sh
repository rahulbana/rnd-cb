#!/usr/bin/env bash
#
# setup.sh — one-shot local setup for the AI Chatbot project.
#
# Does the following:
#   1. Creates a Python 3.12 virtual environment at backend/.venv
#   2. Installs the backend Python dependencies
#   3. Creates backend/.env and frontend/.env from their .env.example files
#      (existing .env files are left untouched)
#   4. Installs the frontend Node dependencies
#
# Usage:
#   ./setup.sh
#
set -euo pipefail

# Resolve the repository root (directory containing this script) so the script
# works no matter where it is invoked from.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# --- helpers ----------------------------------------------------------------
info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

# --- 0. locate Python 3.12 --------------------------------------------------
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif python3 --version 2>&1 | grep -q '3\.12'; then
  PYTHON_BIN="python3"
else
  error "Python 3.12 is required but was not found."
  error "Install it (e.g. 'sudo apt install python3.12 python3.12-venv') and re-run."
  exit 1
fi
info "Using Python: $("$PYTHON_BIN" --version) ($(command -v "$PYTHON_BIN"))"

# --- 1. create virtual environment ------------------------------------------
VENV_DIR="$BACKEND_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
  info "Virtual environment already exists at backend/.venv — reusing it."
else
  info "Creating virtual environment at backend/.venv"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# --- 2. install backend dependencies ----------------------------------------
info "Installing backend Python dependencies"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$BACKEND_DIR/requirements.txt"
deactivate

# --- 3. create .env files from examples -------------------------------------
create_env() {
  local dir="$1"
  local example="$dir/.env.example"
  local target="$dir/.env"
  local label="$2"

  if [ ! -f "$example" ]; then
    warn "$label: no .env.example found, skipping."
    return
  fi
  if [ -f "$target" ]; then
    info "$label: .env already exists — leaving it untouched."
  else
    cp "$example" "$target"
    info "$label: created .env from .env.example"
  fi
}

create_env "$BACKEND_DIR" "backend"
create_env "$FRONTEND_DIR" "frontend"

# --- 4. install frontend dependencies ---------------------------------------
if command -v npm >/dev/null 2>&1; then
  info "Installing frontend Node dependencies"
  (cd "$FRONTEND_DIR" && npm install)
else
  warn "npm not found — skipping frontend dependency install."
  warn "Install Node.js 18+ and run 'cd frontend && npm install' manually."
fi

# --- done -------------------------------------------------------------------
cat <<'EOF'

✅ Setup complete.

Next steps:
  1. Add your OpenAI API key and change the auth password in backend/.env
  2. Start the backend:
       cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
  3. In another terminal, start the frontend:
       cd frontend && npm run dev
  4. Open http://localhost:5173

EOF
