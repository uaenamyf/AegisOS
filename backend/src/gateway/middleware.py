# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 接入统一配置——Trace header 改从 tooling.configs.settings 读取
# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建网关中间件——Trace ID 注入与请求日志
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from tooling.configs.settings import settings

logger = logging.getLogger("aegis.gateway")

TRACE_HEADER = settings.trace.header


class TraceMiddleware(BaseHTTPMiddleware):
    """Ensure every request carries an ``X-Trace-Id`` and log request metadata.

    If the client did not send a trace id, one is generated and stored on
    ``request.state.trace_id`` plus reflected back in the response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get(TRACE_HEADER) or uuid.uuid4().hex
        request.state.trace_id = trace_id

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("trace=%s %s %s ERROR in %.2fms", trace_id, method, path, elapsed)
            raise

        elapsed = (time.perf_counter() - start) * 1000
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
    """Helper to read the trace id attached by ``TraceMiddleware``."""
    return getattr(request.state, "trace_id", "")
