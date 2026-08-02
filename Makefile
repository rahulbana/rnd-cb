.PHONY: help install-mcp install-backend install-frontend mcp backend frontend up down

help:
	@echo "Targets:"
	@echo "  install-mcp       Install MCP server dependencies"
	@echo "  install-backend   Install backend dependencies"
	@echo "  install-frontend  Install frontend dependencies"
	@echo "  mcp               Run the remote MCP server (port 8100)"
	@echo "  backend           Run the FastAPI backend (port 8000)"
	@echo "  frontend          Run the React dev server (port 5173)"
	@echo "  up / down         Start / stop the full stack with docker compose"

install-mcp:
	pip install -r mcp_server/requirements.txt

install-backend:
	pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

mcp:
	cd mcp_server && python -m app.server

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

up:
	docker compose up --build

down:
	docker compose down
