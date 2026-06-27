# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建网关鉴权依赖（API Key，读 gateway.yaml 概念，硬编码 aegis-dev-key）
from __future__ import annotations

from fastapi import Header, HTTPException, Query

# Dev key sourced from tooling/configs/gateway.yaml -> gateway.auth.default_key.
# Hardcoded until a config loader is introduced.
DEV_API_KEY = "aegis-dev-key"
API_KEY_HEADER = "X-API-Key"


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
    api_key: str | None = Query(
        default=None, description="Fallback API key (e.g. for SSE/EventSource)"
    ),
) -> str:
    """Validate the API key from header or query parameter.

    Returns the validated key. Raises 401 when missing/invalid. The query
    fallback exists so browser ``EventSource`` (which cannot set headers) can
    authenticate SSE streams.
    """
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
