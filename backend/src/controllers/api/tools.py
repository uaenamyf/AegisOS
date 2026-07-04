# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 tools 控制器 POST /tools/{name}/invoke（直调工具，不经 Agent 编排）
"""工具直调控制器。

提供 ``POST /tools/{name}/invoke`` 端点，允许直接调用已注册的工具，
无需经过 Agent 编排层，便于调试与运维验证。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.src.composition import ExecutionApiDep
from backend.src.controllers.schemas import InvokeToolRequest
from protocol import ToolCall

# 工具路由器，统一前缀 /tools，标签用于 OpenAPI 文档分组
router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/{name}/invoke")
async def invoke_tool(
    name: str,
    body: InvokeToolRequest,
    execution: ExecutionApiDep,
) -> dict[str, Any]:
    """直接调用指定工具。

    将请求参数封装为 ToolCall 后交由执行 API 同步执行，
    并返回调用结果。调用不经 Agent 编排。

    Args:
        name: 工具名称，作为 URL 路径参数。
        body: 调用请求体，包含参数字典与超时时间。
        execution: 执行 API 依赖，负责实际工具执行。

    Returns:
        包含 ``call_id``、``ok``、``output`` 与 ``error`` 字段的
        字典。``ok`` 为 True 表示调用成功，``error`` 在失败时填充。
    """
    call = ToolCall(name=name, args=body.args, timeout=body.timeout)
    result = execution.execute(call)
    return {
        "call_id": result.call_id,
        "ok": result.ok,
        "output": result.output,
        "error": result.error,
    }
