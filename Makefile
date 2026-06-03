# MCHPAI — top-level orchestration Makefile
# Thin wrappers around docker compose + dev tooling. Every target is idempotent.

SHELL := /bin/bash
COMPOSE := docker compose
PY_SERVICES := token-ingestion wallet-ingestion feature-engine snapshot-engine \
               ground-truth creator-intelligence persistence state-engine \
               graph-engine prediction-engine api-gateway alert-engine \
               ranking-engine strategy-engine
INFRA := nats postgres clickhouse neo4j redis minio prometheus grafana

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
.PHONY: bootstrap
bootstrap: ## Create .env from example and build images
	@test -f .env || cp .env.example .env
	@echo ">> .env ready. Edit secrets before going live."
	$(COMPOSE) build

.PHONY: infra-up
infra-up: ## Start datastores + event bus + observability only
	$(COMPOSE) up -d $(INFRA)

.PHONY: infra-down
infra-down: ## Stop infrastructure
	$(COMPOSE) stop $(INFRA)

.PHONY: up
up: ## Start the whole platform
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop everything
	$(COMPOSE) down

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail logs (use S=service to scope, e.g. make logs S=feature-engine)
	$(COMPOSE) logs -f $(S)

# ---------------------------------------------------------------------------
.PHONY: migrate
migrate: ## Apply Postgres + ClickHouse + Neo4j schemas
	$(COMPOSE) exec -T postgres psql -U mchpai -d mchpai < infrastructure/postgres/init.sql
	$(COMPOSE) exec -T clickhouse clickhouse-client --multiquery < infrastructure/clickhouse/init.sql
	cat infrastructure/neo4j/init.cypher | $(COMPOSE) exec -T neo4j cypher-shell -u neo4j -p mchpai_dev_pw

.PHONY: nats-streams
nats-streams: ## Create JetStream streams/consumers
	bash scripts/create_streams.sh

# ---------------------------------------------------------------------------
.PHONY: lib-install
lib-install: ## Install the shared Python library in editable mode
	pip install -e libraries/mchpai_common

.PHONY: fmt
fmt: ## Format Python + Rust
	-ruff format libraries services || true
	-cargo fmt --manifest-path services/execution-engine/Cargo.toml || true

.PHONY: lint
lint: ## Lint Python + Rust
	-ruff check libraries services || true
	-cargo clippy --manifest-path services/execution-engine/Cargo.toml || true

.PHONY: test
test: ## Run the test suite
	pytest tests/unit tests/integration -q

.PHONY: engine-build
engine-build: ## Build the Rust execution engine (release)
	cargo build --release --manifest-path services/execution-engine/Cargo.toml

# ---------------------------------------------------------------------------
.PHONY: clean
clean: ## Remove build artifacts (keeps data volumes)
	-find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	-cargo clean --manifest-path services/execution-engine/Cargo.toml
