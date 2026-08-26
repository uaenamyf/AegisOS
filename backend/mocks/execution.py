# date: 2026-07-05
# dev: myf
"""MockExecutionAPI — agents.api.ExecutionAPI 的内存占位实现。"""

from __future__ import annotations

from protocol import ToolCall, ToolResult


class MockExecutionAPI:
    """``agents.api.ExecutionAPI`` 的占位实现，返回成功的 mock ToolResult。"""

    def execute(self, call: ToolCall) -> ToolResult:
        """执行工具调用（mock 实现总是返回成功且包含调用名）。"""
        return ToolResult(call_id=call.call_id, ok=True, output={"mock": True, "name": call.name})
