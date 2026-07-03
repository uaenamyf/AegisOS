# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 tools 控制器 POST /tools/{name}/invoke（直调工具，不经 Agent 编排）
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.src.composition import ExecutionApiDep
from backend.src.controllers.schemas import InvokeToolRequest
from protocol import ToolCall

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/{name}/invoke")
async def invoke_tool(
    name: str,
    body: InvokeToolRequest,
    execution: ExecutionApiDep,
) -> dict[str, Any]:
    call = ToolCall(name=name, args=body.args, timeout=body.timeout)
    result = execution.execute(call)
    return {
        "call_id": result.call_id,
        "ok": result.ok,
        "output": result.output,
        "error": result.error,
    }
