# WC Fantasy 2026 — Docker / DB helpers
# Usage: make <target>

COMPOSE ?= docker compose
PROJECT ?= wc-fantasy
VOLUME  ?= wc_fantasy_sqlite

BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTEST := $(BACKEND_DIR)/.venv/bin/pytest
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PIP := $(BACKEND_DIR)/.venv/bin/pip

.PHONY: help build up down remove migrate migrate-force logs ps restart sync shell-backend shell-db \
	test test-backend test-frontend test-cov test-backend-cov test-frontend-cov test-install

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

build: ## Build backend + frontend images
	$(COMPOSE) build

up: ## Start stack (detached); creates tables/seeds on backend boot
	@test -f .env || (echo "Tip: copy .env.example -> .env if you have not yet"; true)
	@mkdir -p data
	@test -f data/quiniela.csv || (test -f quinierla.csv && cp quinierla.csv data/quiniela.csv || true)
	$(COMPOSE) up -d
	@echo ""
	@echo "Frontend: http://localhost:3000"
	@echo "API docs: http://localhost:8000/docs"

down: ## Stop containers (keeps images + SQLite volume)
	$(COMPOSE) down

remove: ## Stop and remove containers, networks, images; asks before deleting DB volume
	$(COMPOSE) down --rmi local --remove-orphans
	@echo ""
	@echo "SQLite volume '$(VOLUME)' is still on disk (persistent data)."
	@echo "To delete it permanently: make remove-volume"

remove-volume: ## DANGER: delete the SQLite named volume (all DB data)
	@echo "This will delete $(VOLUME) and all scores/predictions."
	@read -p "Type 'yes' to confirm: " ans && [ "$$ans" = "yes" ] || (echo "Aborted."; exit 1)
	$(COMPOSE) down
	docker volume rm $(VOLUME) 2>/dev/null || docker volume rm $$(docker volume ls -q --filter name=$(VOLUME)) 2>/dev/null || true
	@echo "Volume removed."

migrate: ## Ensure schema exists + seed CSV if DB is empty (safe, non-destructive)
	@echo "Running migrate (create tables + seed if empty)..."
	@$(COMPOSE) ps --status running --services 2>/dev/null | grep -q backend || \
		(echo "Backend not running; starting temporarily..." && $(COMPOSE) up -d backend && sleep 3)
	$(COMPOSE) exec -T backend python -c "\
from app.database import Base, engine, SessionLocal; \
from app.seed import seed_if_empty; \
Base.metadata.create_all(bind=engine); \
db = SessionLocal(); \
r = seed_if_empty(db); \
db.close(); \
print(r)"

migrate-force: ## DANGER: wipe predictions/matches and re-seed from CSV (keeps admin user if possible)
	@echo "Force re-seed: clears matches/predictions and re-imports quiniela.csv"
	@read -p "Type 'yes' to confirm: " ans && [ "$$ans" = "yes" ] || (echo "Aborted."; exit 1)
	@$(COMPOSE) ps --status running --services 2>/dev/null | grep -q backend || \
		(echo "Backend not running; starting temporarily..." && $(COMPOSE) up -d backend && sleep 3)
	$(COMPOSE) exec -T backend python -c "\
from app.database import Base, engine, SessionLocal; \
from app.models import Prediction, Match, User; \
from app.seed import seed_if_empty; \
from app.scoring import recalculate_all_scores; \
Base.metadata.create_all(bind=engine); \
db = SessionLocal(); \
db.query(Prediction).delete(); \
db.query(Match).delete(); \
db.query(User).filter(User.is_admin == False).delete(); \
db.commit(); \
r = seed_if_empty(db); \
recalculate_all_scores(db); \
db.commit(); \
db.close(); \
print(r)"

sync: ## Force fetch finished scores (FBref/Wikipedia/API) and update leaderboard
	@$(COMPOSE) ps --status running --services 2>/dev/null | grep -q backend || \
		(echo "Start the stack first: make up"; exit 1)
	$(COMPOSE) exec -T backend python -c "\
import asyncio; \
from app.results_sync import sync_finished_scores; \
print(asyncio.run(sync_finished_scores(force_all=True)))"

logs: ## Tail all service logs
	$(COMPOSE) logs -f

ps: ## Show container status
	$(COMPOSE) ps

restart: ## Restart all services
	$(COMPOSE) restart

shell-backend: ## Open a shell in the backend container
	$(COMPOSE) exec backend /bin/sh

# ── Tests (local, no e2e) ────────────────────────────────

test-install: ## Install backend + frontend test dependencies
	@test -x $(PYTHON) || (cd $(BACKEND_DIR) && python3 -m venv .venv && $(PIP) install -q -r requirements-dev.txt)
	@$(PIP) install -q -r $(BACKEND_DIR)/requirements-dev.txt
	@npm install --silent 2>/dev/null || npm install
	@echo "Test deps ready."

test-backend: ## Run backend unit tests (pytest, fast)
	@test -x $(PYTEST) || $(MAKE) test-install
	cd $(BACKEND_DIR) && .venv/bin/pytest -q

test-backend-cov: ## Backend tests with coverage report (terminal + html)
	@test -x $(PYTEST) || $(MAKE) test-install
	cd $(BACKEND_DIR) && .venv/bin/pytest -q \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:coverage_html \
		--cov-fail-under=80
	@echo "Backend HTML coverage: $(BACKEND_DIR)/coverage_html/index.html"

test-frontend: ## Run frontend unit tests (jest, fast)
	npm run test -w frontend -- --passWithNoTests

test-frontend-cov: ## Frontend tests with coverage
	npm run test:coverage -w frontend

test: ## Run all unit tests quickly (backend + frontend, no coverage gate)
	@$(MAKE) test-backend
	@$(MAKE) test-frontend
	@echo "All unit tests passed."

test-cov: ## Full unit test suite with coverage (backend + frontend)
	@$(MAKE) test-backend-cov
	@$(MAKE) test-frontend-cov
	@echo "Coverage complete."

# Default target
.DEFAULT_GOAL := help
