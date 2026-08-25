# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 Makefile，定义 setup/test/build/deploy 等自动化命令

.PHONY: setup test test-unit test-integration lint typecheck format dev frontend-setup frontend-dev frontend-build gen-types clean ci check broadcast-check all

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
	uvicorn backend.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend-dev:
	cd frontend && npm run dev

format:
	ruff format .
	ruff check --fix .

# P3.3 baseline: 158 错误（E402 import 顺序 / E731 lambda / F821 既有），
# 按 §11 AI 范围 P3.4 专项治理。CI 用 continue-on-error 汇报不 fail。
lint:
	ruff check .

typecheck:
	mypy protocol aegisos_agents backend --ignore-missing-imports

test:
	pytest

# P3.3: 低熵广播静态检测（spec 04 §16 / 11 §7 铁律守卫；CI 必跑）
# 退出码: 0=无违规, 1=--strict 模式违规, 2=配置错误
broadcast-check:
	$(PYTHON) tooling/scripts/check_no_broadcast.py --strict

# P3.3: 一键本地复现 CI 流水线（lint + broadcast-check + test）
# 与 .github/workflows/ci.yml 严格对齐
check: lint broadcast-check test
	@echo "All CI checks passed."

# P3.3: CI 流水线代理（开发者直接 make ci 看日志）
ci:
	@echo "See .github/workflows/ci.yml — runs on push/PR via GitHub Actions."
	@echo "Local equivalent: make check"

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
