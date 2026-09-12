# date: 2026-07-07
# dev: myf
"""SDK Tracing 基础设施包 —— 自定义 TracingProcessor + AgentHooks。

导出：
    - :class:`CyberTraceProcessor` — 采集 SDK trace/span 事件
    - :class:`CyberTraceData` — trace 聚合数据
    - :class:`CyberSpanData` — span 采集数据
    - :class:`CyberAgentHooks` — Agent 生命周期钩子
    - :class:`HookEvent` — 钩子事件数据
"""

from .hooks import CyberAgentHooks, HookEvent
from .processor import CyberSpanData, CyberTraceData, CyberTraceProcessor

__all__ = [
    "CyberTraceProcessor",
    "CyberTraceData",
    "CyberSpanData",
    "CyberAgentHooks",
    "HookEvent",
]
