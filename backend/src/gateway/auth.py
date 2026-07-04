# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 接入统一配置——API Key/header 改从 tooling.configs.settings 读取
# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建网关鉴权依赖（API Key，读 gateway.yaml 概念，硬编码 aegis-dev-key）
"""网关 API Key 鉴权依赖。

本模块为 FastAPI 路由提供基于 API Key 的鉴权依赖。鉴权凭据可来自请求头
（默认 ``X-API-Key``）或查询参数（兼容无法自定义请求头的浏览器 EventSource）。
凭据来源统一从 :mod:`tooling.configs.settings` 读取，支持环境变量 > .env >
defaults.yaml 的多级配置覆盖。
"""
from __future__ import annotations

from fastapi import Header, HTTPException, Query

from tooling.configs.settings import settings

# 配置来源：tooling/configs/settings.py（优先级：env > .env > defaults.yaml）。
DEV_API_KEY = settings.auth.default_key
# 用于读取 API Key 的请求头名称（默认 X-API-Key）。
API_KEY_HEADER = settings.auth.api_key_header


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
    api_key: str | None = Query(
        default=None, description="Fallback API key (e.g. for SSE/EventSource)"
    ),
) -> str:
    """校验请求头或查询参数中的 API Key。

    优先从请求头读取 API Key；若请求头缺失，则回退到查询参数 ``api_key``。
    查询参数回退主要用于浏览器 ``EventSource``（无法自定义请求头）访问 SSE
    流式接口时的鉴权。

    Args:
        x_api_key: 请求头中的 API Key，字段名由 ``API_KEY_HEADER`` 决定。
        api_key: 查询参数中的备选 API Key，用于 SSE/EventSource 场景。

    Returns:
        校验通过的 API Key 字符串。

    Raises:
        HTTPException: 当 API Key 缺失时抛出 401（code=AUTH_FAILED,
            message=missing API key）；当 API Key 不匹配时抛出 401
            （code=AUTH_FAILED, message=invalid API key）。
    """
    # 优先使用请求头中的 key，缺失时回退到查询参数。
    key = x_api_key or api_key
    if not key:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_FAILED", "message": "missing API key"},
        )
    if key != DEV_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_FAILED", "message": "invalid API key"},
        )
    return key
