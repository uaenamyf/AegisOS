#!/bin/bash
# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建一键启动脚本，同时拉起后端(FastAPI)和前端(Vite)
# AegisOS 一键启动脚本
# 用法: ./start.sh           启动前后端
#       ./start.sh backend   仅启动后端
#       ./start.sh frontend  仅启动前端
#       ./start.sh stop      停止所有

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 加载统一配置（tooling/configs/.env），未找到则使用默认值
if [ -f "$PROJECT_ROOT/tooling/configs/.env" ]; then
    set -a
    . "$PROJECT_ROOT/tooling/configs/.env"
    set +a
fi

PYTHON="${AEGIS_PYTHON:-/opt/anaconda3/bin/python3.13}"
NPM="${AEGIS_NPM:-/opt/homebrew/bin/npm}"
BACKEND_PORT="${AEGIS_BACKEND_PORT:-8000}"
FRONTEND_PORT="${AEGIS_FRONTEND_PORT:-5173}"
PID_FILE="/tmp/aegisos_pids"

export PATH="/opt/homebrew/bin:$PATH"

start_backend() {
    echo "[backend] Starting FastAPI on :$BACKEND_PORT ..."
    cd "$PROJECT_ROOT"
    $PYTHON -m uvicorn backend.src.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
    echo "$! backend" >> "$PID_FILE"
    sleep 2
    # Health check
    if curl -sf "http://127.0.0.1:$BACKEND_PORT/api/v1/health" > /dev/null 2>&1; then
        echo "[backend] ✅ Running at http://localhost:$BACKEND_PORT"
        echo "[backend]   Health:  GET  http://localhost:$BACKEND_PORT/api/v1/health"
        echo "[backend]   API docs: http://localhost:$BACKEND_PORT/docs"
        echo "[backend]   API key: X-API-Key: aegis-dev-key"
    else
        echo "[backend] ❌ Failed to start — check logs"
    fi
}

start_frontend() {
    echo "[frontend] Starting Vite dev server on :$FRONTEND_PORT ..."
    cd "$PROJECT_ROOT/frontend"
    $NPM run dev -- --port $FRONTEND_PORT &
    echo "$! frontend" >> "$PID_FILE"
    sleep 3
    echo "[frontend] ✅ Running at http://localhost:$FRONTEND_PORT"
}

stop_all() {
    if [ -f "$PID_FILE" ]; then
        while read pid name; do
            if kill "$pid" 2>/dev/null; then
                echo "[$name] Stopped (pid $pid)"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    else
        echo "No running processes found."
    fi
}

case "${1:-all}" in
    backend)
        start_backend
        echo ""
        echo "Press Ctrl+C to stop."
        wait
        ;;
    frontend)
        start_frontend
        echo ""
        echo "Press Ctrl+C to stop."
        wait
        ;;
    stop)
        stop_all
        ;;
    all|*)
        echo "╔══════════════════════════════════════════╗"
        echo "║   AegisOS — Starting (Backend + Frontend) ║"
        echo "╚══════════════════════════════════════════╝"
        echo ""
        start_backend
        echo ""
        start_frontend
        echo ""
        echo "──────────────────────────────────────────"
        echo "  Backend:  http://localhost:$BACKEND_PORT"
        echo "  Frontend: http://localhost:$FRONTEND_PORT"
        echo "  API docs: http://localhost:$BACKEND_PORT/docs"
        echo "  API key:  aegis-dev-key"
        echo "──────────────────────────────────────────"
        echo ""
        echo "Press Ctrl+C to stop both."
        echo ""
        # Cleanup on exit
        trap 'echo ""; stop_all; exit 0' INT TERM
        wait
        ;;
esac
