# date: 2026-07-07
# dev: myf
"""SDK Tracing 数据采集器 —— 自定义 TracingProcessor 收集编排全链路 trace/span。

本模块实现 :class:`CyberTraceProcessor`，继承 SDK ``TracingProcessor`` 抽象类，
在 SDK ``trace()`` 上下文管理器或 ``Runner.run()`` 调用时自动被回调，
收集 trace 和 span 的事件数据，供 ``observability/inspect/replay/`` 时序回放消费。

工作原理：
    1. 通过 ``set_trace_processors([processor])`` 注册到 SDK 全局
    2. SDK 在 ``trace()`` 上下文进入时调用 ``on_trace_start(trace)``
    3. SDK 在每个 span（Agent 调用 / LLM 调用 / 工具调用）开始/结束时
       调用 ``on_span_start(span)`` / ``on_span_end(span)``
    4. ``trace()`` 退出时调用 ``on_trace_end(trace)``
    5. 调用方通过 :meth:`CyberTraceProcessor.get_trace_data` 获取聚合数据

设计决策：
    - 不依赖 OpenAI 云端 trace export（``OPENAI_API_KEY`` 未设置时 SDK 自动跳过）
    - 全部数据在内存中聚合，适合单元测试和本地可视化
    - ``reset()`` 方法清空状态，支持多次编排调用独立采集
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from agents import TracingProcessor

# date: 2026-07-07
# dev: myf
# changelog: 新建 CyberTraceProcessor + CyberTraceData + CyberSpanData


@dataclass
class CyberSpanData:
    """单个 span 的采集数据。

    Attributes:
        span_id: SDK 生成的 span ID。
        parent_id: 父 span ID（顶层为 None）。
        name: span 名称。
        type: span 类型（``agent`` / ``generation`` / ``function`` / ``guardrail`` / ``handoff`` / ``response``）。
        started_at: span 开始时间戳。
        ended_at: span 结束时间戳（未结束为 None）。
        data: span 的结构化数据（从 ``span.export()`` 获取）。
        error: span 错误信息（如果有）。
    """

    span_id: str = ""
    parent_id: str | None = None
    name: str = ""
    type: str = ""
    started_at: float = 0.0
    ended_at: float | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典。"""
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "type": self.type,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": (
                round((self.ended_at - self.started_at) * 1000, 2)
                if self.ended_at is not None
                else None
            ),
            "data": self.data,
            "error": self.error,
        }


@dataclass
class CyberTraceData:
    """单个 trace 的聚合数据。

    Attributes:
        trace_id: SDK 生成的 trace ID。
        workflow_name: 工作流名称（``trace(workflow_name=...)`` 传入）。
        group_id: 分组 ID（可选）。
        metadata: trace 元数据。
        spans: 该 trace 下所有 span 的列表。
        started_at: trace 开始时间戳。
        ended_at: trace 结束时间戳（未结束为 None）。
    """

    trace_id: str = ""
    workflow_name: str = ""
    group_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    spans: list[CyberSpanData] = field(default_factory=list)
    started_at: float = 0.0
    ended_at: float | None = None

    @property
    def span_count(self) -> int:
        """span 总数。"""
        return len(self.spans)

    @property
    def duration_ms(self) -> float | None:
        """trace 总耗时（毫秒），未结束为 None。"""
        if self.ended_at is None:
            return None
        return round((self.ended_at - self.started_at) * 1000, 2)

    def spans_by_type(self, span_type: str) -> list[CyberSpanData]:
        """按类型筛选 span。"""
        return [s for s in self.spans if s.type == span_type]

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典。"""
        return {
            "trace_id": self.trace_id,
            "workflow_name": self.workflow_name,
            "group_id": self.group_id,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "span_count": self.span_count,
            "spans": [s.to_dict() for s in self.spans],
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False, indent=2)


class CyberTraceProcessor(TracingProcessor):
    """自定义 TracingProcessor —— 采集 SDK trace/span 事件到内存。

    使用方式::

        processor = CyberTraceProcessor()
        set_trace_processors([processor])

        with trace(workflow_name="cyber_red_chain", metadata={"scenario": "s1"}):
            orchestrator.run_red_chain("10.0.0.0/24")

        data = processor.get_trace_data()
        print(data.to_json())

    Attributes:
        _traces: 当前活跃的 trace（trace_id → CyberTraceData）。
        _completed: 已完成的 trace 列表。
    """

    def __init__(self) -> None:
        """初始化采集器。"""
        self._traces: dict[str, CyberTraceData] = {}
        self._completed: list[CyberTraceData] = []

    def on_trace_start(self, trace: Any) -> None:
        """trace 开始时回调。

        Args:
            trace: SDK Trace 对象，含 ``name`` (workflow_name) / ``trace_id`` /
                ``group_id`` / ``metadata`` 属性。
        """
        trace_id = getattr(trace, "trace_id", "")
        # SDK Trace.name 就是 workflow_name
        workflow_name = getattr(trace, "name", "")
        group_id = getattr(trace, "group_id", None)
        metadata = getattr(trace, "metadata", {}) or {}

        data = CyberTraceData(
            trace_id=trace_id,
            workflow_name=workflow_name,
            group_id=group_id,
            metadata=dict(metadata),
            started_at=time.time(),
        )
        self._traces[trace_id] = data

    def on_trace_end(self, trace: Any) -> None:
        """trace 结束时回调。"""
        trace_id = getattr(trace, "trace_id", "")
        data = self._traces.pop(trace_id, None)
        if data is not None:
            data.ended_at = time.time()
            self._completed.append(data)

    def on_span_start(self, span: Any) -> None:
        """span 开始时回调。"""
        # 找到当前活跃 trace（取最后一个）
        if not self._traces:
            return
        # span 关联到 trace_id
        span_trace_id = getattr(span, "trace_id", None)
        if span_trace_id and span_trace_id in self._traces:
            trace_data = self._traces[span_trace_id]
        else:
            # 取最后一个活跃 trace
            trace_data = list(self._traces.values())[-1]

        span_data = CyberSpanData(
            span_id=getattr(span, "span_id", ""),
            parent_id=getattr(span, "parent_id", None),
            name=getattr(span, "name", ""),
            type=self._extract_span_type(span),
            started_at=time.time(),
            data=self._export_span_data(span),
        )
        trace_data.spans.append(span_data)

    def on_span_end(self, span: Any) -> None:
        """span 结束时回调。"""
        span_id = getattr(span, "span_id", "")
        # 在所有活跃 trace 中找到这个 span 并更新
        for trace_data in self._traces.values():
            for s in reversed(trace_data.spans):
                if s.span_id == span_id and s.ended_at is None:
                    s.ended_at = time.time()
                    s.data = self._export_span_data(span)
                    s.error = self._extract_span_error(span)
                    return

    def force_flush(self) -> None:
        """强制刷新（无缓冲，空实现）。"""
        pass

    def shutdown(self) -> None:
        """关闭时清理资源。"""
        self._traces.clear()

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def get_trace_data(self) -> CyberTraceData | None:
        """获取最近完成的 trace 数据。

        Returns:
            最近的 :class:`CyberTraceData`；无完成的 trace 时返回 None。
        """
        if self._completed:
            return self._completed[-1]
        return None

    def get_all_traces(self) -> list[CyberTraceData]:
        """获取所有已完成的 trace 列表。"""
        return list(self._completed)

    def reset(self) -> None:
        """清空所有采集数据。"""
        self._traces.clear()
        self._completed.clear()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_span_type(span: Any) -> str:
        """从 span 对象中提取类型字符串。

        SDK span 的 ``span_data`` 属性有 ``type`` 字段标识 span 类型。
        """
        span_data = getattr(span, "span_data", None)
        if span_data is not None:
            # span_data 可能是 dataclass 或对象
            if hasattr(span_data, "type"):
                return span_data.type
            if isinstance(span_data, dict):
                return span_data.get("type", "")
        return getattr(span, "name", "")

    @staticmethod
    def _export_span_data(span: Any) -> dict[str, Any]:
        """导出 span 数据为字典。"""
        try:
            export_fn = getattr(span, "export", None)
            if export_fn is not None:
                data = export_fn()
                if isinstance(data, dict):
                    return data
                if data is not None:
                    return {"exported": str(data)}
        except Exception:
            pass
        return {
            "span_id": getattr(span, "span_id", ""),
            "name": getattr(span, "name", ""),
        }

    @staticmethod
    def _extract_span_error(span: Any) -> str | None:
        """从 span 中提取错误信息。"""
        span_data = getattr(span, "span_data", None)
        if span_data is not None:
            error = getattr(span_data, "error", None)
            if error is not None:
                return str(error)
        return None
