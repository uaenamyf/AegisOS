# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 接入统一配置——CORS/logging/version 改从 tooling.configs.settings 读取
# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 FastAPI 应用入口——CORS/Trace 中间件/网关路由/WS/统一错误格式/lifespan DB 初始化
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.src.composition import get_composition
from backend.src.controllers.api.health import router as health_router
from backend.src.controllers.ws.stream import router as ws_router
from backend.src.gateway.middleware import TraceMiddleware, get_trace_id
from backend.src.gateway.routes import router as gateway_router
from tooling.configs.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper(), logging.INFO),
    format=settings.logging.format,
)

# CORS origins sourced from tooling/configs/settings.py (env > .env > defaults.yaml).
_CORS_ORIGINS = list(settings.cors.origins)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB; Shutdown: dispose engine."""
    comp = get_composition()
    await comp.startup()
    logging.getLogger("aegis.main").info("AegisOS backend started (version 0.1.0)")
    try:
        yield
    finally:
        await comp.shutdown()
        logging.getLogger("aegis.main").info("AegisOS backend stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="AegisOS Backend", version=settings.backend.version, lifespan=lifespan)

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceMiddleware)

    # --- Routes ---
    # Health is public (no auth) — mounted directly on app.
    app.include_router(health_router, prefix="/api/v1")
    # Gateway (/api/v1/* with auth) provides /sessions, /tasks, /agents, ...
    app.include_router(gateway_router)
    # WebSocket lives outside /api/v1 (spec: ws://host/ws/v1/stream).
    app.include_router(ws_router)

    # --- Unified error format: {"code", "message", "trace_id"} ---
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        trace_id = get_trace_id(request)
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", _code_for_status(exc.status_code))
            message = exc.detail.get("message", "")
        else:
            code = _code_for_status(exc.status_code)
            message = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": message, "trace_id": trace_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("aegis.main").exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL",
                "message": "internal server error",
                "trace_id": get_trace_id(request),
            },
        )

    return app


def _code_for_status(status_code: int) -> str:
    return {
        400: "INVALID_REQUEST",
        401: "AUTH_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL",
    }.get(status_code, f"HTTP_{status_code}")


app = create_app()
