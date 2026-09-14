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
（会阻塞事件循环）。这里用 ``asyncio.to_thread`` 把同步编排放到线程池。

事件回传采用**可重放的事件历史**（``_history`` + ``threading.Condition``），
而非旧的单消费 ``queue.Queue``：SSE 订阅者按 cursor 增量读取，先回放历史再等
待新事件，因此「切走再切回」「Chat 发起后面板接管」等任意时刻接入都能看到
完整的已发生过程。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
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
        # 事件历史 + 条件变量：替代旧的单消费队列。
        # 旧实现用 queue.Queue，事件一旦被某个 SSE 连接消费即丢失，导致
        # 「切走再切回 / Chat 发起后面板接管」时新订阅者只能收到未来的事件，
        # 已经发生过的 drill_start / drill_stage / drill_agent 永远收不到，
        # 前端 CoT 时间线空白、卡在「等待首个 agent 启动」。
        # 现在所有事件留档在 _history，订阅者按 cursor 增量读取：先回放历史，
        # 再阻塞等待新事件，任意时刻接入都能看到完整推理过程。
        self._history: list[dict[str, Any]] = []
        self._cond = threading.Condition()
        # 运行中轮次内存暂存：get_drill 在记录落盘前也能返回实时进度
        self.rounds: list[dict[str, Any]] = []
        self.abort_evt = threading.Event()
        self.state = "running"  # running | done | aborted
        self.summary: dict[str, Any] | None = None
        self.error: str | None = None
        # 实时进度快照：供 get_drill 在「切页返回」时恢复阶段/轮次/耗时
        self.current_round = 0
        self.current_stage: str | None = None
        self.started_at = time.time()

    def emit(self, event: str, data: dict[str, Any]) -> None:
        """把一条 SSE 事件写入历史并唤醒所有订阅者（支持任意时刻重放）。"""
        with self._cond:
            self._history.append({"event": event, "data": data})
            self._cond.notify_all()

    def wait_events(
        self, cursor: int, timeout: float = 1.0
    ) -> tuple[list[dict[str, Any]], bool]:
        """返回 ``cursor`` 之后的事件批次。

        无新事件时阻塞至多 ``timeout`` 秒。第二个返回值表示流已终止
        （编排线程已结束且历史排空），调用方据此关闭 SSE。
        """
        with self._cond:
            if cursor >= len(self._history) and self.state == "running":
                self._cond.wait(timeout=timeout)
            batch = self._history[cursor:]
            done = self.state != "running" and cursor + len(batch) >= len(
                self._history
            )
            return batch, done

    def agent_trace(self) -> list[dict[str, Any]]:
        """从事件历史提取 CoT agent 轨迹，供 get_drill 返回。

        前端切页返回时用它恢复「推理过程」时间线，不再空白显示
        「等待首个 agent 启动」。
        """
        with self._cond:
            return [
                item["data"]
                for item in self._history
                if item["event"] == "drill_agent"
            ]

    # ---- CoT/ToT 可视化：agent 级事件 ----

    # 每个 agent 的人类可读职责描述（前端 CoT 时间线直接展示）
    _AGENT_LABELS: dict[str, str] = {
        "recon": "侦察资产",
        "vuln_correlator": "关联漏洞",
        "exploit_planner": "规划攻击链",
        "detector": "检测入侵",
        "triage": "告警分诊",
        "threat_hunt": "威胁狩猎",
        "ir_planner": "制定响应",
        "critic": "攻击链校验",
        "reviewer": "一致性审查",
    }

    def _emit_agent(self, stage: str, agent: str) -> None:
        """发一个 agent 开始执行的 CoT 事件（SSE + 全局总线）。"""
        data = {
            "drill_id": self.drill_id,
            "stage": stage,
            "agent": agent,
            "label": self._AGENT_LABELS.get(agent, agent),
            "round": self.current_round,
            "ts": time.time(),
        }
        self.emit("drill_agent", data)
        with contextlib.suppress(Exception):
            self.event_bus.publish(
                Event(
                    event_type=EventType.DrillAgent,
                    task_id=self.drill_id,
                    payload=data,
                )
            )

    def _emit_stage(self, stage: str, round_no: int) -> None:
        """记录当前阶段并推送阶段级事件（供切页返回后恢复进度）。"""
        self.current_stage = stage
        self.current_round = round_no or self.current_round
        self.emit(
            "drill_stage",
            {"stage": stage, "round": round_no, "drill_id": self.drill_id},
        )

    def _publish_status(self, status: str) -> None:
        """演练状态变更发布到全局总线（供 Monitor 派生活跃状态）。"""
        with contextlib.suppress(Exception):
            self.event_bus.publish(
                Event(
                    event_type=EventType.DrillStatus,
                    task_id=self.drill_id,
                    payload={"drill_id": self.drill_id, "status": status},
                )
            )

    # ---- 编排线程入口 ----

    def _run(self) -> None:
        """在后台线程执行编排，逐事件投递到 SSE 队列。"""
        try:
            def abort() -> bool:
                return self.abort_evt.is_set()

            def on_round(round_data: dict[str, Any], round_no: int) -> None:
                self.rounds.append(round_data)
                self.current_round = round_no
                self.current_stage = None
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

            self.emit(
                "drill_start",
                {"drill_id": self.drill_id, "max_rounds": self.max_rounds},
            )
            # CoT/ToT 可视化：演练运行状态发布到全局总线，供 Monitor 派生
            # Agent 活跃状态（不再永远 idle）
            self._publish_status("running")
            # R18d：mock 演示多轮趋势——强制至少展示 min_rounds 轮再判收敛；
            # 真实 LLM 保持 0（越快收敛越好），两种模式互不影响。
            try:
                from backend.core import runtime_mode as _rm
                _mode = _rm.get_mode()
            except Exception:  # noqa: BLE001
                _mode = "mock"
            _min_rounds = min(self.max_rounds, 4) if _mode == "mock" else 0
            result = self.service.drill(
                self.target_range,
                max_rounds=self.max_rounds,
                on_round=on_round,
                abort=abort,
                drill_id=self.drill_id,
                min_rounds=_min_rounds,
                on_stage=lambda stage, r: self._emit_stage(stage, r),
                on_agent=lambda stage, agent: self._emit_agent(
                    stage, agent
                ),
            )
            self.summary = result.get("summary") or {}
            self.emit("drill_summary", self.summary)
            self.emit("drill_done", {"drill_id": self.drill_id})
            self.state = "done"
            self._publish_status("done")
            # 自动落盘运行记录报告（每轮红/蓝/紫产物 + 卸载轨迹 + 收敛总结）
            with contextlib.suppress(Exception):
                write_drill_report(result)
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self.emit("drill_error", {"error": str(exc)})
            self.emit("drill_done", {"drill_id": self.drill_id, "error": True})
            self.state = "aborted"
            self._publish_status("error")

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
        """SSE 生成器：按 cursor 读取事件历史，先回放再等新增。

        任意时刻接入（切页返回 / Chat 发起后接管）都能拿到已发生的全过程。
        """
        cursor = 0
        while True:
            batch, done = await asyncio.to_thread(runtime.wait_events, cursor)
            for item in batch:
                cursor += 1
                yield DrillRuntime._sse_frame(item["event"], item["data"])
            if done:
                return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/list")
async def list_drills(service: CyberDefenseServiceDep) -> dict[str, Any]:
    """列出本地持久化的全部演练记录（元信息，不含完整战报）。

    Returns:
        ``{"drills": [...]}``，按生成时间倒序；每个元素含
        ``drill_id`` / ``target_range`` / ``rounds_executed`` /
        ``convergence_code`` / ``created_at``。
    """
    return {"drills": service.list_drills()}


@router.get("/{drill_id}")
async def get_drill(drill_id: str, service: CyberDefenseServiceDep) -> dict[str, Any]:
    """查询演练状态与已发生轮次（SSE 断开时的轮询兜底）。

    历史演练（进程内无 runtime）回退读取落盘记录，供历史列表/对比使用。

    Args:
        drill_id: 演练 ID。
        service: 攻防服务依赖。

    Returns:
        已落盘的演练记录；未完成则返回当前运行态摘要。
    """
    runtime = _RUNTIMES.get(drill_id)
    record = service.get_drill(drill_id)
    if runtime is None:
        # 历史演练：直接返回落盘记录（T7 对比视图的数据源）
        if record:
            return {
                "drill_id": drill_id,
                "status": "done",
                "max_rounds": record.get("max_rounds", record.get("rounds_executed", 0)),
                "target_range": record.get("target_range", ""),
                "rounds": record["rounds"],
                "rounds_executed": len(record["rounds"]),
                "convergence_code": record.get("convergence_code"),
                "summary": record.get("summary"),
                "created_at": record.get("created_at"),
                "error": None,
            }
        raise HTTPException(status_code=404, detail=f"Drill not found: {drill_id}")
    return {
        "drill_id": drill_id,
        "status": runtime.state,
        "max_rounds": runtime.max_rounds,
        "target_range": runtime.target_range,
        "rounds": record["rounds"] if record else runtime.rounds,
        "rounds_executed": len(record["rounds"]) if record else len(runtime.rounds),
        "convergence_code": (
            record["convergence_code"]
            if record
            else (runtime.summary or {}).get("convergence_code")
        ),
        "summary": runtime.summary,
        "error": runtime.error,
        # 切页返回时恢复实时进度：当前阶段 + CoT agent 轨迹 + 已进时间
        "current_stage": runtime.current_stage,
        "current_round": runtime.current_round,
        "elapsed": round(time.time() - runtime.started_at, 1),
        "agent_trace": runtime.agent_trace(),
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
    record = service.get_drill(drill_id)
    if not record:
        raise HTTPException(status_code=404, detail="Drill record not found")
    from backend.services.drill_report import build_drill_report_json

    return build_drill_report_json(record)


@router.get("/{drill_id}/report.pdf")
async def drill_report_pdf(drill_id: str, service: CyberDefenseServiceDep):
    """以 PDF 文件下载演练运行记录报告（替代浏览器打印预览）。

    使用 reportlab 内置 STSong-Light CID 字体渲染中文，返回
    ``application/pdf`` 附件供前端 blob 下载为真正的 .pdf 文件。
    """
    from fastapi.responses import Response

    from backend.services.drill_report import build_drill_report_json

    record = service.get_drill(drill_id)
    if not record:
        raise HTTPException(status_code=404, detail="Drill record not found")
    report_md = build_drill_report_json(record)["report_md"]

    pdf_bytes = _render_report_pdf(report_md, drill_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="aegis-drill-{drill_id}.pdf"'
        },
    )


def _render_report_pdf(report_md: str, drill_id: str) -> bytes:
    """把 Markdown 战报渲染为 PDF 字节流（reportlab + STSong-Light CID 中文）。"""
    from io import BytesIO

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    buff = BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"AegisOS Drill Report {drill_id}",
    )
    body = ParagraphStyle(
        "body", fontName="STSong-Light", fontSize=9.5, leading=15, spaceAfter=6
    )
    h1 = ParagraphStyle("h1", parent=body, fontSize=15, leading=20, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=body, fontSize=12.5, leading=17, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=body, fontSize=10.5, leading=15, spaceAfter=4)

    story: list = []
    rows: list[list[str]] = []
    for raw in report_md.split("\n"):
        line = raw.rstrip("\r")
        stripped = line.strip()
        if not stripped:
            rows.append([])  # 空行：若正处于表格，则输出表格后继续
            continue
        esc = (
            stripped.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        if stripped.startswith("#"):
            lv = min(len(stripped) - len(stripped.lstrip("#")), 3)
            style = [h1, h2, h3][lv - 1]
            story.append(Paragraph(esc.lstrip("# "), style))
        elif stripped.startswith("|"):
            # 表格行
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if any(set(c) <= set(":- ") for c in cells):
                continue  # 分隔行
            rows.append([Paragraph(c, body) for c in cells])
        elif stripped.startswith(("- ", "* ", "1. ")):
            story.append(Spacer(1, 2))
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(esc[2:], body), leftIndent=10)],
                    bulletType="bullet",
                    start="•",
                )
            )
        elif stripped.startswith("```"):
            continue
        else:
            story.append(Paragraph(esc, body or h3))
    if rows:
        t = Table(rows, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, "#999"),
                    ("BACKGROUND", (0, 0), (-1, 0), "#eef3fb"),
                ]
            )
        )
        story.append(t)
    doc.build(story)
    return buff.getvalue()


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
    runtime = _RUNTIMES.get(drill_id)
    record = service.get_drill(drill_id)
    if runtime is None and not record:
        raise HTTPException(status_code=404, detail=f"Drill not found: {drill_id}")
    if record and record.get("summary"):
        return record["summary"]
    if runtime is not None and runtime.summary:
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
