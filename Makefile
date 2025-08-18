.PHONY: help up down build test format lint typecheck clean logs

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d --build

down: ## Stop all services
	docker compose down -v

build: ## Build all services
	docker compose build

test: ## Run tests
	docker compose run --rm mcp-nautobot pytest
	docker compose run --rm chat-ui python -m pytest

format: ## Format code
	docker compose run --rm mcp-nautobot black .
	docker compose run --rm mcp-nautobot isort .
	docker compose run --rm chat-ui black .
	docker compose run --rm chat-ui isort .

lint: ## Lint code
	docker compose run --rm mcp-nautobot ruff check .
	docker compose run --rm chat-ui ruff check .

typecheck: ## Type check code
	docker compose run --rm mcp-nautobot mypy .
	docker compose run --rm chat-ui mypy .

clean: ## Clean up containers and volumes
	docker compose down -v --remove-orphans
	docker system prune -f

logs: ## Show logs from all services
	docker compose logs -f

logs-mcp: ## Show MCP server logs
	docker compose logs -f mcp-nautobot

logs-chat: ## Show chat UI logs
	docker compose logs -f chat-ui

logs-nautobot: ## Show Nautobot logs
	docker compose logs -f nautobot

shell-mcp: ## Open shell in MCP server container
	docker compose exec mcp-nautobot bash

shell-chat: ## Open shell in chat UI container
	docker compose exec chat-ui bash

shell-nautobot: ## Open shell in Nautobot container
	docker compose exec nautobot bash 