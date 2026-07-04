# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 接入统一配置——CORS/logging/version 改从 tooling.configs.settings 读取
# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 FastAPI 应用入口——CORS/Trace 中间件/网关路由/WS/统一错误格式/lifespan DB 初始化
"""AegisOS 后端 FastAPI 应用入口。

本模块负责创建并配置 FastAPI 应用实例，包括：日志初始化、CORS 跨域、
Trace ID 中间件、健康检查/网关/WebSocket 路由挂载、统一错误响应格式化，
以及基于 lifespan 的数据库引擎初始化与释放。配置统一从
:mod:`tooling.configs.settings` 读取，支持环境变量 > .env > defaults.yaml
的多级覆盖。
"""
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

# 日志级别与格式从统一配置读取；级别字符串映射到 logging 模块常量。
logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper(), logging.INFO),
    format=settings.logging.format,
)

# CORS 来源从 tooling/configs/settings.py 读取（env > .env > defaults.yaml）。
_CORS_ORIGINS = list(settings.cors.origins)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库，停止时释放引擎。

    Args:
        app: 当前 FastAPI 应用实例（此处未直接使用，保留参数以符合 lifespan 协议）。

    Yields:
        无返回值；yield 之前的逻辑在启动时执行，之后的逻辑在关闭时执行。
    """
    comp = get_composition()
    await comp.startup()
    logging.getLogger("aegis.main").info("AegisOS backend started (version 0.1.0)")
    try:
        yield
    finally:
        await comp.shutdown()
        logging.getLogger("aegis.main").info("AegisOS backend stopped")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    组装中间件（CORS、Trace）、挂载路由（健康检查、网关、WebSocket），
    并注册统一格式的异常处理器。

    Returns:
        配置完成的 :class:`fastapi.FastAPI` 应用实例。
    """
    app = FastAPI(title="AegisOS Backend", version=settings.backend.version, lifespan=lifespan)

    # --- 中间件 ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceMiddleware)

    # --- 路由 ---
    # 健康检查为公开接口（无需鉴权），直接挂载到 app 上。
    app.include_router(health_router, prefix="/api/v1")
    # 网关（/api/v1/*，带鉴权）提供 /sessions、/tasks、/agents 等接口。
    app.include_router(gateway_router)
    # WebSocket 不在 /api/v1 下（规范：ws://host/ws/v1/stream）。
    app.include_router(ws_router)

    # --- 统一错误格式：{"code", "message", "trace_id"} ---
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """将 HTTPException 转换为统一格式的 JSON 响应。

        Args:
            request: 触发异常的请求对象，用于读取 trace id。
            exc: 捕获的 HTTPException。

        Returns:
            统一格式的 :class:`fastapi.responses.JSONResponse`，包含
            ``code``、``message`` 与 ``trace_id`` 三个字段。
        """
        trace_id = get_trace_id(request)
        # detail 若为 dict，则允许调用方自定义 code/message。
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
        """兜底处理所有未捕获异常，返回 500 统一错误响应。

        Args:
            request: 触发异常的请求对象，用于读取 trace id。
            exc: 捕获的未处理异常。

        Returns:
            状态码 500 的统一格式 :class:`fastapi.responses.JSONResponse`。
        """
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
    """将 HTTP 状态码映射为业务错误码字符串。

    Args:
        status_code: HTTP 状态码（如 404、422）。

    Returns:
        对应的业务错误码字符串（如 ``NOT_FOUND``）；未匹配时返回
        ``HTTP_<status_code>``。
    """
    return {
        400: "INVALID_REQUEST",
        401: "AUTH_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL",
    }.get(status_code, f"HTTP_{status_code}")


# 模块级应用实例，供 uvicorn 通过 backend.src.main:app 加载。
app = create_app()
