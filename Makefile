.PHONY: install dev test lint run cli db-up db-down clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check app tests
	ruff format --check app tests

run:
	uvicorn app.main:app --reload --port 8000

cli:
	@# usage: make cli TOPIC="Nvidia data-center moat"
	research "$(TOPIC)" $(ARGS)

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache build dist *.egg-info
