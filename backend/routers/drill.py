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

from backend.core.composition import CyberDefenseServiceDep

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

    def __init__(self, service, target_range: str, max_rounds: int) -> None:
        self.drill_id = f"drill-{uuid.uuid4().hex[:8]}"
        self.target_range = target_range
        self.max_rounds = max_rounds
        self.service = service
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
        "summary": runtime.summary,
        "error": runtime.error,
    }


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
