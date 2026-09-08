# date: 2026-09-04
# dev: AegisOS Dev
# changelog: R3 新建多轮演练 drill 路由——REST(sync) + SSE(stream) 编排入口
"""多轮攻防演练（CyberDrill）路由。

提供一键「开始演练→多轮收敛→总结报告」的编排入口：

- ``POST /api/v1/drill/start`` —— 启动一场多轮演练（后台线程跑同步编排，
  立刻返回 ``drill_id``）。
- ``GET  /api/v1/drill/{id}/stream`` —— SSE 实时推流：``drill_start →
  drill_round* → drill_summary → drill_done``，任一轮异常推 ``drill_error``。
- ``GET  /api/v1/drill/{id}`` —— 查询已发生轮次 + 当前状态（轮询兜底）。
- ``GET  /api/v1/drill/{id}/summary`` —— 收敛后的总结报告；未完成返回 409。
- ``POST /api/v1/drill/{id}/abort`` —— 请求中止（收敛规则 4）。

并发模型（评审修订）：编排器为**同步**逻辑，不可直接 ``asyncio.create_task``
（会阻塞事件循环）。这里用 ``asyncio.to_thread`` 把同步编排放到线程池，
每轮经**线程安全** ``queue.Queue`` + ``asyncio.to_thread(q.get)`` 回传给 SSE，
既不阻塞 FastAPI 事件循环，也保持 SSE 流式响应模型。
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.composition import CyberDefenseServiceDep, get_composition
from backend.services.drill_report import write_drill_report
from protocol import Event
from protocol.event import EventType

router = APIRouter(prefix="/drill", tags=["cyber-defense"])


class DrillStartRequest(BaseModel):
    """开始演练请求体。"""

    target_range: str = "10.0.0.0/24"
    max_rounds: int = 5


class DrillRuntime:
    """单场演练的运行时状态（内存 registry 条目）。

    负责：为 SSE 提供线程安全的逐事件队列；为中止提供跨线程 flag；
    记录演练状态、目标与总结。编排跑在 ``asyncio.to_thread`` 的线程里，
    on_round 回调经 ``q.put`` 投递事件，SSE 生成器经 ``to_thread(q.get)`` 消费。
    """

    def __init__(
        self, service, target_range: str, max_rounds: int, event_bus=None
    ) -> None:
        self.drill_id = f"drill-{uuid.uuid4().hex[:8]}"
        self.target_range = target_range
        self.max_rounds = max_rounds
        self.service = service
        # R9: 事件总线注入；None 时取全局 composition 单例（/events SSE 可订阅）
        self.event_bus = event_bus if event_bus is not None else get_composition().event_bus
        self.events: queue.Queue[dict[str, Any]] = queue.Queue()
        self.abort_evt = threading.Event()
        self.state = "running"  # running | done | aborted
        self.summary: dict[str, Any] | None = None
        self.error: str | None = None

    def emit(self, event: str, data: dict[str, Any]) -> None:
        """把一条 SSE 事件投递到线程安全队列。"""
        self.events.put({"event": event, "data": data})

    # ---- 编排线程入口 ----

    def _run(self) -> None:
        """在后台线程执行编排，逐事件投递到 SSE 队列。"""
        try:
            def abort() -> bool:
                return self.abort_evt.is_set()

            def on_round(round_data: dict[str, Any], round_no: int) -> None:
                self.emit("drill_round", {"round": round_no, **round_data})
                # R9: 低熵增量事件发布到 EventBus——payload 只含增量与摘要，
                # 不含全量 AttackChain/ResponsePlan，抑制通信冗余。
                self.event_bus.publish(
                    Event(
                        event_type=EventType.DrillRound,
                        task_id=self.drill_id,
                        payload={
                            "round": round_no,
                            "drill_id": self.drill_id,
                            "new_steps": len(
                                round_data.get("red", {}).get("new_steps", [])
                            ),
                            "new_issues": round_data.get("purple", {}).get(
                                "new_issue_count", 0
                            ),
                            "valid": round_data.get("purple", {}).get("valid", False),
                            "converged": round_data.get("purple", {}).get(
                                "converged", False
                            ),
                            "carry_forward_count": sum(
                                1
                                for e in round_data.get("event_stream", [])
                                if isinstance(e, dict) and e.get("carry_forward")
                            ),
                            "prior_summary": round_data.get("prior_rounds_summary"),
                        },
                    )
                )

            self.emit("drill_start", {"drill_id": self.drill_id, "max_rounds": self.max_rounds})
            result = self.service.drill(
                self.target_range,
                max_rounds=self.max_rounds,
                on_round=on_round,
                abort=abort,
                drill_id=self.drill_id,
            )
            self.summary = result.get("summary") or {}
            self.emit("drill_summary", self.summary)
            self.emit("drill_done", {"drill_id": self.drill_id})
            self.state = "done"
            # 自动落盘运行记录报告（每轮红/蓝/紫产物 + 卸载轨迹 + 收敛总结）
            try:
                write_drill_report(result)
            except Exception:  # noqa: BLE001 —— 报告生成失败不影响演练结果
                pass
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self.emit("drill_error", {"error": str(exc)})
            self.emit("drill_done", {"drill_id": self.drill_id, "error": True})
            self.state = "aborted"

    @staticmethod
    def _sse_frame(event: str, data: dict[str, Any]) -> str:
        """把事件转成 SSE 帧。"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# 内存 runtime registry：drill_id -> DrillRuntime。仅保留最近 128 条防无界增长。
_RUNTIMES: dict[str, DrillRuntime] = {}
_RUNTIME_ORDER: list[str] = []
_MAX_RUNTIMES = 128


def _register(runtime: DrillRuntime) -> None:
    _RUNTIMES[runtime.drill_id] = runtime
    _RUNTIME_ORDER.append(runtime.drill_id)
    while len(_RUNTIME_ORDER) > _MAX_RUNTIMES:
        oldest = _RUNTIME_ORDER.pop(0)
        _RUNTIMES.pop(oldest, None)


def _get_runtime(drill_id: str) -> DrillRuntime:
    runtime = _RUNTIMES.get(drill_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"Drill not found: {drill_id}")
    return runtime


@router.post("/start", status_code=201)
async def start_drill(
    body: DrillStartRequest,
    service: CyberDefenseServiceDep,
) -> dict[str, Any]:
    """启动一场多轮演练，后台线程执行，立即返回 drill_id。

    Args:
        body: 含目标网络范围与最大轮数。
        service: 攻防服务依赖。

    Returns:
        ``{drill_id, status:"running", max_rounds}``。
    """
    runtime = DrillRuntime(service, body.target_range, body.max_rounds)
    _register(runtime)
    # 同步编排放线程池，不阻塞事件循环
    asyncio.get_running_loop().run_in_executor(None, runtime._run)
    return {"drill_id": runtime.drill_id, "status": "running", "max_rounds": body.max_rounds}


@router.get("/{drill_id}/stream")
async def stream_drill(drill_id: str) -> StreamingResponse:
    """SSE 实时推送演练战报。

    Args:
        drill_id: 演练 ID。

    Returns:
        ``text/event-stream``：``drill_start → drill_round* → drill_summary →
        drill_done``；异常推 ``drill_error`` 后收尾。
    """
    runtime = _get_runtime(drill_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 生成器：从线程安全队列消费事件。"""
        while True:
            item = await asyncio.to_thread(runtime.events.get)
            yield DrillRuntime._sse_frame(item["event"], item["data"])
            if item["event"] == "drill_done":
                return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{drill_id}")
async def get_drill(drill_id: str, service: CyberDefenseServiceDep) -> dict[str, Any]:
    """查询演练状态与已发生轮次（SSE 断开时的轮询兜底）。

    Args:
        drill_id: 演练 ID。
        service: 攻防服务依赖。

    Returns:
        已落盘的演练记录；未完成则返回当前运行态摘要。
    """
    runtime = _get_runtime(drill_id)
    record = service.get_drill(runtime.drill_id)
    return {
        "drill_id": drill_id,
        "status": runtime.state,
        "max_rounds": runtime.max_rounds,
        "target_range": runtime.target_range,
        "rounds": record["rounds"] if record else [],
        "rounds_executed": len(record["rounds"]) if record else 0,
        "convergence_code": (
            record["convergence_code"]
            if record
            else (runtime.summary or {}).get("convergence_code")
        ),
        "summary": runtime.summary,
        "error": runtime.error,
    }


@router.get("/{drill_id}/report")
async def drill_report(drill_id: str, service: CyberDefenseServiceDep) -> dict[str, Any]:
    """获取演练的运行记录报告（每轮红/蓝/紫产物 + 卸载轨迹 + 收敛总结）。

    Args:
        drill_id: 演练 ID。
        service: 攻防服务依赖。

    Raises:
        HTTPException: 演练记录不存在返回 404。

    Returns:
        ``{drill_id, report_md, rounds_executed, convergence_code, raw_json_path}``。
    """
    runtime = _get_runtime(drill_id)
    record = service.get_drill(runtime.drill_id)
    if not record:
        raise HTTPException(status_code=404, detail="Drill record not found")
    from backend.services.drill_report import build_drill_report_json

    return build_drill_report_json(record)


@router.get("/{drill_id}/summary")
async def drill_summary(drill_id: str, service: CyberDefenseServiceDep) -> dict[str, Any]:
    """取收敛后的总结报告。

    Args:
        drill_id: 演练 ID。
        service: 攻防服务依赖。

    Raises:
        HTTPException: 尚未完成收敛返回 409。

    Returns:
        演练总结报告。
    """
    runtime = _get_runtime(drill_id)
    record = service.get_drill(runtime.drill_id)
    if record and record.get("summary"):
        return record["summary"]
    if runtime.summary:
        return runtime.summary
    raise HTTPException(status_code=409, detail="Drill not converged yet")


@router.post("/{drill_id}/abort")
async def abort_drill(drill_id: str) -> dict[str, Any]:
    """请求中止演练（收敛规则 4：当前轮边界后停止并输出已收敛部分总结）。

    Args:
        drill_id: 演练 ID。

    Returns:
        ``{drill_id, status:"aborted"}``。
    """
    runtime = _get_runtime(drill_id)
    if runtime.state == "running":
        runtime.abort_evt.set()
    return {"drill_id": drill_id, "status": "aborted"}
