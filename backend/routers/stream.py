# date: 2026-07-07
# dev: myf
# changelog: R5.3 新建 SDK 流式 SSE router——Runner.run_streamed() → SSE 实时推送 Agent 思考过程
"""SDK 流式 SSE 控制器 —— 实时推送 Agent 执行过程到前端。

R5.3：用 SDK ``Runner.run_streamed()`` 替代 ``Runner.run_sync()``，
逐事件 yield 为 SSE 帧，前端可实时看到 Agent 的思考过程、handoff、工具调用。

端点：
    - ``POST /api/v1/stream/agent/{agent_id}`` — 流式执行指定 Agent
    - ``POST /api/v1/stream/red_chain`` — 流式执行红队攻击链
    - ``POST /api/v1/stream/blue_chain`` — 流式执行蓝队防御链

SSE 帧格式::
    event: <event_type>
    data: <json>

事件类型（SDK StreamEvent）：
    - ``agent_updated`` — Agent 切换（handoff）
    - ``run_item`` — 产出项（消息/工具调用/输出）
    - ``raw_response`` — 原始模型响应
    - ``error`` — 执行异常

注意：
    - Mock 模式下 ``MockSDKModel`` 不支持流式（NotImplementedError），
      此时会回退到同步执行并一次性返回结果。
    - 真实 API 模式下可看到逐 token 流式输出。
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import is_dataclass
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.composition import get_composition


def _asdict(obj):
    return obj.model_dump() if isinstance(obj, BaseModel) else obj

router = APIRouter(prefix="/stream", tags=["stream"])


def _serialize(obj: Any) -> Any:
    """将任意对象序列化为 JSON 兼容类型。"""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if is_dataclass(obj) and not isinstance(obj, type):
        return _asdict(obj)
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _event_to_sse(event: Any, event_type: str = "run_item") -> str:
    """将 SDK StreamEvent 序列化为 SSE 帧。"""
    try:
        data = _serialize(event)
    except Exception:  # noqa: BLE001
        data = {"repr": repr(event)}
    return f"event: {event_type}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"


@router.post("/agent/{agent_id}")
async def stream_agent(
    agent_id: str,
    body: dict[str, Any] | None = None,
) -> StreamingResponse:
    """流式执行指定 Agent，逐事件 SSE 推送。

    Args:
        agent_id: 目标 Agent ID（如 ``recon`` / ``detector`` 等）。
        body: 请求体，可含 ``prompt`` 字段。

    Returns:
        ``StreamingResponse``（``text/event-stream``），逐事件推送 SSE 帧。
    """
    prompt = (body or {}).get("prompt", f"Execute agent: {agent_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 帧生成器。"""
        try:
            comp = get_composition()
            runtime = comp.runtime
            # 获取单 Agent 实例
            agent_map = {
                "recon": runtime._recon,
                "detector": runtime._detector,
                "vuln_correlator": runtime._vuln_correlator,
                "exploit_planner": runtime._exploit_planner,
                "lateral_move": runtime._lateral_move,
                "triage": runtime._triage,
                "threat_hunt": runtime._threat_hunt,
                "ir_planner": runtime._ir_planner,
                "forensics": runtime._forensics,
                "critic": runtime._critic,
                "reviewer": runtime._reviewer,
            }
            agent = agent_map.get(agent_id)
            if agent is None:
                yield _event_to_sse({"error": f"Unknown agent: {agent_id}"}, "error")
                return

            # 尝试流式执行
            try:
                async for event in agent._run_streamed(prompt):
                    event_type = type(event).__name__
                    yield _event_to_sse(event, event_type)
            except NotImplementedError:
                # Mock 模式不支持流式，回退到同步
                result = agent._run(prompt)
                yield _event_to_sse({"final_output": _serialize(result)}, "final")
        except Exception as exc:  # noqa: BLE001
            yield _event_to_sse({"error": str(exc)}, "error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/red_chain")
async def stream_red_chain(body: dict[str, Any] | None = None) -> StreamingResponse:
    """流式执行红队攻击链，逐步 SSE 推送。

    Args:
        body: 请求体，可含 ``target_range`` 字段。

    Returns:
        ``StreamingResponse``，逐步推送 recon → vuln_correlator → exploit_planner 的产出。
    """
    target_range = (body or {}).get("target_range", "10.0.0.0/24")

    async def event_generator() -> AsyncGenerator[str, None]:
        """红队链 SSE 帧生成器。"""
        try:
            comp = get_composition()
            orchestrator = comp.orchestrator

            yield _event_to_sse({"phase": "recon", "target": target_range}, "phase_start")
            # 红队链用同步方法（Mock 兼容），逐步推送产出
            result = orchestrator.run_red_chain(target_range)
            yield _event_to_sse(
                {"phase": "recon", "assets": _serialize(result["assets"])}, "phase_done"
            )
            yield _event_to_sse(
                {"phase": "vuln_correlator", "findings": _serialize(result["findings"])},
                "phase_done",
            )
            yield _event_to_sse(
                {"phase": "exploit_planner", "chain": _serialize(result["chain"])},
                "phase_done",
            )
            yield _event_to_sse({"status": "completed"}, "final")
        except Exception as exc:  # noqa: BLE001
            yield _event_to_sse({"error": str(exc)}, "error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/blue_chain")
async def stream_blue_chain(body: dict[str, Any] | None = None) -> StreamingResponse:
    """流式执行蓝队防御链，逐步 SSE 推送。

    Args:
        body: 请求体，可含 ``event_stream`` 字段。

    Returns:
        ``StreamingResponse``，逐步推送 detector → triage → threat_hunt → ir_planner 的产出。
    """
    event_stream = (body or {}).get("event_stream", [])

    async def event_generator() -> AsyncGenerator[str, None]:
        """蓝队链 SSE 帧生成器。"""
        try:
            comp = get_composition()
            orchestrator = comp.orchestrator

            result = orchestrator.run_blue_chain(event_stream)
            yield _event_to_sse(
                {"phase": "detector", "alerts": _serialize(result["alerts"])}, "phase_done"
            )
            yield _event_to_sse(
                {"phase": "triage", "triaged": _serialize(result["triaged"])}, "phase_done"
            )
            yield _event_to_sse(
                {"phase": "threat_hunt", "hypotheses": result["hypotheses"]}, "phase_done"
            )
            yield _event_to_sse(
                {"phase": "ir_planner", "plan": _serialize(result["plan"])}, "phase_done"
            )
            yield _event_to_sse({"status": "completed"}, "final")
        except Exception as exc:  # noqa: BLE001
            yield _event_to_sse({"error": str(exc)}, "error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
