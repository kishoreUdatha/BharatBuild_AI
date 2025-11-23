.PHONY: help setup start stop restart logs clean test migrate shell db-shell redis-shell

help:
	@echo "BharatBuild AI - Makefile Commands"
	@echo ""
	@echo "Setup & Start:"
	@echo "  make setup       - Initial setup (creates .env, pulls images)"
	@echo "  make start       - Start all services"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo ""
	@echo "Development:"
	@echo "  make logs        - View all logs"
	@echo "  make shell       - Open backend shell"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make redis-shell - Open Redis shell"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run database migrations"
	@echo "  make migrate-create - Create new migration"
	@echo "  make migrate-down - Rollback last migration"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make test-backend - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Stop services and remove volumes"
	@echo "  make clean-all   - Remove everything including images"

setup:
	@echo "Setting up BharatBuild AI..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please edit it with your API keys."; \
	fi
	docker-compose pull
	@echo "Setup complete!"

start:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started! Access:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000/docs"

stop:
	@echo "Stopping all services..."
	docker-compose down

restart:
	@echo "Restarting all services..."
	docker-compose restart

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

shell:
	docker-compose exec backend /bin/bash

db-shell:
	docker-compose exec postgres psql -U bharatbuild -d bharatbuild_db

redis-shell:
	docker-compose exec redis redis-cli

migrate:
	@echo "Running database migrations..."
	docker-compose exec backend alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	docker-compose exec backend alembic revision --autogenerate -m "$$msg"

migrate-down:
	docker-compose exec backend alembic downgrade -1

test:
	@echo "Running all tests..."
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend:
	@echo "Running backend tests..."
	docker-compose exec backend pytest

test-frontend:
	@echo "Running frontend tests..."
	docker-compose exec frontend npm test

lint-backend:
	docker-compose exec backend black app
	docker-compose exec backend flake8 app

lint-frontend:
	docker-compose exec frontend npm run lint

clean:
	@echo "Cleaning up..."
	docker-compose down -v

clean-all:
	@echo "Removing everything..."
	docker-compose down -v --rmi all

build:
	@echo "Building all images..."
	docker-compose build

rebuild:
	@echo "Rebuilding all images..."
	docker-compose build --no-cache

ps:
	docker-compose ps

stats:
	docker stats

health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "Backend not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend is up" || echo "Frontend not responding"
