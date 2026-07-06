# date: 2026-06-27
# dev: myf
"""健康检查控制器。

提供 ``GET /health`` 端点，用于探活与版本探测，供负载均衡器、
Kubernetes liveness/readiness 探针或运维监控调用。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

# 健康检查路由器，标签用于 OpenAPI 文档分组
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """健康探活端点。

    返回服务运行状态与版本号，仅用于探活，不依赖任何后端资源。

    Returns:
        包含 ``status`` 与 ``version`` 字段的字典。``status`` 取值
        ``ok`` 表示服务可用，``version`` 为当前后端版本号。
    """
    return {"status": "ok", "version": "0.1.0"}
