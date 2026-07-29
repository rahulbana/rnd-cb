.PHONY: install dev mcp-server chat seed test lint fmt clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# Start the remote SQLite MCP server (streamable-HTTP on :8000/mcp)
mcp-server:
	python -m mcp_server.server

# Interactive chat with the agent (needs the MCP server running + OPENAI_API_KEY)
chat:
	python -m agentic_app.main

seed:
	python scripts/seed_clients.py

test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff format .

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
