# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 Makefile，定义 setup/test/build/deploy 等自动化命令

.PHONY: setup test test-unit test-integration lint typecheck format dev frontend-setup frontend-dev frontend-build gen-types clean

PYTHON := python3
PIP := $(PYTHON) -m pip
BACKEND_HOST ?= 0.0.0.0
BACKEND_PORT ?= 8000

setup:
	$(PIP) install -e ".[dev]"
	@echo "Python dependencies installed."

frontend-setup:
	cd frontend && npm install
	@echo "Frontend dependencies installed."

dev:
	uvicorn backend.src.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend-dev:
	cd frontend && npm run dev

format:
	ruff format .
	ruff check --fix .

lint:
	ruff check .

typecheck:
	mypy protocol agents backend --ignore-missing-imports

test:
	pytest

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

gen-types:
	$(PYTHON) tooling/scripts/gen_ts_types.py
	@echo "TypeScript types generated."

frontend-build:
	cd frontend && npm run build

build: frontend-build
	@echo "Build complete."

deploy:
	@echo "Deploy not implemented yet. Use: docker-compose up"
	@echo "See developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md §B5"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
