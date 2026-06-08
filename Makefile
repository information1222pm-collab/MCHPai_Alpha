.PHONY: help install test lint demo infra-up infra-down api

help:
	@echo "MCHPAI Advanced Wallet Intelligence System"
	@echo "  make install    create venv and install dev deps"
	@echo "  make test       run the test suite"
	@echo "  make lint       run ruff"
	@echo "  make demo       run the in-memory observatory tour"
	@echo "  make api        serve the read-only observatory API"
	@echo "  make infra-up   start local infrastructure (docker compose)"
	@echo "  make infra-down stop local infrastructure"

install:
	uv venv
	uv pip install -e '.[dev,api,research]'

test:
	PYTHONPATH=src python -m pytest -q

# Live-service conformance. Bring infra up first (make infra-up) and export the
# WIS_* connection vars; adapters not configured are skipped, not failed.
test-integration:
	PYTHONPATH=src python -m pytest -q -m integration -rs

lint:
	ruff check src tests

demo:
	PYTHONPATH=src python -m wis.app.demo

api:
	uvicorn 'wis.app.api.server:create_app' --factory --reload

infra-up:
	docker compose -f deploy/docker-compose.yml up -d

infra-down:
	docker compose -f deploy/docker-compose.yml down
