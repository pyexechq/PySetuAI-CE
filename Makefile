# PySetuAI — Docker helpers
# Run `make help` for a list of targets.
#
# WHY dot_clean: This repo lives on an external macOS volume. macOS creates
# hidden AppleDouble sidecar files (._*) with xattr metadata that Docker's
# BuildKit cannot read → "failed to xattr … operation not permitted".
# dot_clean merges those into the parent file's resource fork and removes the
# sidecars, making the build context clean for every run.

.PHONY: help clean build build-backend build-frontend up down restart migrate \
        logs logs-backend logs-frontend ps

# Always pass .env.docker so NEXT_PUBLIC_API_URL and other overrides are applied
COMPOSE := docker compose --env-file .env.docker

# ── targets ────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  PySetuAI Docker helpers"
	@echo ""
	@echo "  make build            dot_clean + build ALL services"
	@echo "  make build-backend    dot_clean + build backend only"
	@echo "  make build-frontend   dot_clean + build frontend only"
	@echo "  make up               start all services (no rebuild)"
	@echo "  make down             stop and remove all containers"
	@echo "  make restart          down + build + up"
	@echo "  make migrate          run alembic upgrade head"
	@echo "  make logs             tail all service logs"
	@echo "  make logs-backend     tail backend logs"
	@echo "  make logs-frontend    tail frontend logs"
	@echo "  make ps               show container status"
	@echo "  make clean            remove ._* files and __pycache__"
	@echo ""

# ── dot_clean helper (internal) ────────────────────────────────────────────────

.clean-apple-files:
	@echo "→ Cleaning macOS AppleDouble / xattr sidecar files…"
	@dot_clean .
	@find . -name "._*" -delete
	@find . -name ".DS_Store" -delete
	@find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "  Done."

# ── public targets ─────────────────────────────────────────────────────────────

clean: .clean-apple-files

build: .clean-apple-files
	$(COMPOSE) up -d --build

build-backend: .clean-apple-files
	$(COMPOSE) up -d --build backend

build-frontend: .clean-apple-files
	$(COMPOSE) up -d --build frontend

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart: down build

migrate:
	@echo "→ Running Alembic migrations…"
	$(COMPOSE) exec backend alembic upgrade head

logs:
	$(COMPOSE) logs -f

logs-backend:
	$(COMPOSE) logs -f backend

logs-frontend:
	$(COMPOSE) logs -f frontend

ps:
	$(COMPOSE) ps
