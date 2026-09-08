# date: 2026-07-04
# dev: myf
"""网关中间件：Trace ID 注入与请求日志。

本模块实现 ``TraceMiddleware``，为每个请求生成或复用追踪 ID，并将其附加到
``request.state`` 及响应头中，便于跨服务链路追踪。同时记录请求方法、路径、
状态码与耗时，便于性能监控与问题定位。Trace 头名称统一从
:mod:`tooling.configs.settings` 读取。
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tooling.configs.settings import settings

# 网关日志器，独立于业务日志。
logger = logging.getLogger("aegis.gateway")

# Trace ID 所使用的请求/响应头名称，由统一配置提供。
TRACE_HEADER = settings.trace.header


class TraceMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 Trace ID 并记录请求元数据与耗时。

    若客户端未携带 Trace ID，则生成一个 UUID4 十六进制串作为新的追踪 ID。
    该 ID 会写入 ``request.state.trace_id``，供后续依赖（如错误处理）读取，
    并回写到响应头中返回给客户端。同时记录请求方法、路径、状态码与处理
    耗时（毫秒）。

    Attributes:
        无额外属性；继承自 BaseHTTPMiddleware。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """处理单个请求：注入 Trace ID、调用下游、记录日志。

        Args:
            request: 当前 Starlette 请求对象。
            call_next: 下一个中间件或路由处理协程。

        Returns:
            经过 Trace 头增强的响应对象。

        Raises:
            任何下游抛出的异常都会被记录日志后重新抛出，不在此吞没。
        """
        # 优先复用客户端传入的 trace id，否则生成新的。
        trace_id = request.headers.get(TRACE_HEADER) or uuid.uuid4().hex
        request.state.trace_id = trace_id

        # 记录起始时间用于计算请求耗时。
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            # 下游抛异常时记录错误日志，并兜底返回统一 500（不 re-raise）：
            # re-raise 会让 ServerErrorMiddleware 生成 500，该响应不经过 CORS
            # 中间件，浏览器会误报“无 Access-Control-Allow-Origin”；此处返回后
            # 响应仍会经过 CORSMiddleware 补上跨域头。
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("trace=%s %s %s ERROR in %.2fms", trace_id, method, path, elapsed)
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL",
                    "message": "internal server error",
                    "trace_id": trace_id,
                },
            )

        elapsed = (time.perf_counter() - start) * 1000
        # 将 trace id 回写到响应头，便于客户端关联日志。
        response.headers[TRACE_HEADER] = trace_id
        logger.info(
            "trace=%s %s %s %s in %.2fms",
            trace_id,
            method,
            path,
            response.status_code,
            elapsed,
        )
        return response


def get_trace_id(request: Request) -> str:
    """读取由 ``TraceMiddleware`` 注入到 ``request.state`` 的 Trace ID。

    Args:
        request: 当前请求对象。

    Returns:
        Trace ID 字符串；若未经过中间件注入则返回空字符串。
    """
    return getattr(request.state, "trace_id", "")
