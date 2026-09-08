# date: 2026-09-04
# dev: OpenSquilla
# changelog: R7 新建——运行时模式控制器（GET/POST /system/mode）
"""运行时模式控制器 —— 查询/切换攻防编排器运行模式（mock / 真实 LLM）。

端点：
- GET  /api/v1/system/mode  → 当前模式描述（供前端徽标展示）
- POST /api/v1/system/mode  → 切换模式（body: {"mode": "mock"|"real"}）
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core import runtime_mode
from backend.core.auth import verify_api_key

router = APIRouter(prefix="/system", tags=["system"], dependencies=[Depends(verify_api_key)])


class SetModeRequest(BaseModel):
    """切换模式请求体。"""

    mode: Literal["mock", "real"] = Field(..., description="目标模式：mock=预置响应 / real=真实 LLM")


class SetApiKeyRequest(BaseModel):
    """云侧 LLM API Key 配置请求体。"""

    api_key: str = Field(..., description="云侧 LLM API Key（如 DeepSeek sk-...）")


# 环境变量文件：后端 main.py 后台线程每 15s 热重载，写后无需重启即生效
_ENV_PATH = Path("tooling/configs/.env")


def _persist_env_key(api_key: str) -> None:
    """把 ``OPENAI_API_KEY`` upsert 进 ``tooling/configs/.env``（幂等）。"""
    _ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines() if _ENV_PATH.exists() else []
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.strip().startswith("OPENAI_API_KEY"):
            out.append(f"OPENAI_API_KEY={api_key}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"OPENAI_API_KEY={api_key}")
    _ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


@router.get("/mode")
async def get_mode() -> dict[str, Any]:
    """返回当前运行时模式描述（模式/模型/提供商/Key 可用性）。"""
    return runtime_mode.describe()


@router.post("/mode")
async def set_mode(body: SetModeRequest) -> dict[str, Any]:
    """切换运行时模式并返回新描述。"""
    try:
        runtime_mode.set_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_MODE", "message": str(exc)},
        ) from exc
    return runtime_mode.describe()


@router.post("/api-key")
async def set_api_key(body: SetApiKeyRequest) -> dict[str, Any]:
    """配置云侧 LLM API Key：写入环境变量文件 + 立即生效 + 重建 real 编排器。

    前端「运行配置」输入 Key 后调用本端点，后端同步到 ``tooling/configs/.env``
    （main.py 后台线程 15s 内热重载）并即时刷入进程环境变量，随后丢弃缓存的
    real 编排器使新 Key 生效；端/边暂不单独配置，统一走云 API。

    Args:
        body: 含 ``api_key`` 的请求体。

    Returns:
        配置后的模式描述（含 ``has_key`` 状态，不回显 Key 本身）。
    """
    key = body.api_key.strip()
    if len(key) < 8:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_API_KEY", "message": "api_key too short"},
        )
    try:
        _persist_env_key(key)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "ENV_WRITE_FAILED", "message": str(exc)},
        ) from exc
    os.environ["OPENAI_API_KEY"] = key
    # 丢弃缓存的 real 编排器：下次 get_orchestrator() 用新 Key 重建
    runtime_mode.invalidate("real")
    return runtime_mode.describe()
