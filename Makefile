# ============================================================
# Digital FTE — Makefile
# Common development commands
#
# Usage: make <target>
#   make up          Start the full stack (builds if needed)
#   make down        Stop everything
#   make build       Rebuild Docker images
#   make logs        Stream all logs
#   make restart     Restart services
#   make shell-back  Open shell inside backend container
#   make shell-front Open shell inside frontend container
#   make dev-back    Run backend locally (no Docker)
#   make dev-front   Run frontend locally (no Docker)
# ============================================================

.PHONY: up down build logs restart shell-back shell-front dev-back dev-front clean help

help:
	@echo ""
	@echo "  Digital FTE — Available Commands"
	@echo "  ──────────────────────────────────────────"
	@echo "  make up           Start full stack (Docker)"
	@echo "  make down         Stop all services"
	@echo "  make build        Force rebuild Docker images"
	@echo "  make logs         Stream logs from all services"
	@echo "  make logs-back    Stream backend logs only"
	@echo "  make logs-front   Stream frontend logs only"
	@echo "  make restart      Restart all services"
	@echo "  make shell-back   Shell into backend container"
	@echo "  make shell-front  Shell into frontend container"
	@echo "  make dev-back     Run backend locally (no Docker)"
	@echo "  make dev-front    Run frontend locally (no Docker)"
	@echo "  make clean        Remove containers, volumes, images"
	@echo "  make env          Copy .env.example → .env (if missing)"
	@echo ""

up:
	docker compose up -d

build:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-back:
	docker compose logs -f backend

logs-front:
	docker compose logs -f frontend

restart:
	docker compose restart

shell-back:
	docker compose exec backend /bin/bash

shell-front:
	docker compose exec frontend /bin/sh

# ── Local development (no Docker) ──────────────────────────

dev-back:
	@echo "Starting backend locally on port 8080..."
	cd backend && \
	    python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

dev-front:
	@echo "Starting frontend locally on port 5173..."
	cd frontend && npm run dev

dev-install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# ── Utilities ──────────────────────────────────────────────

env:
	@if [ ! -f .env ]; then \
	    cp .env.example .env; \
	    echo "Created .env from template. Edit it with your API keys."; \
	else \
	    echo ".env already exists."; \
	fi

clean:
	@echo "Removing containers, volumes, and images..."
	docker compose down -v --rmi local
	@echo "Done. Run 'make build' to start fresh."
