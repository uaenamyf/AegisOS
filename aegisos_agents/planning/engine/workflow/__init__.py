# date: 2026-07-06
# dev: myf
"""DAG 工作流引擎包。

导出 :class:`WorkflowEngine` 及相关类型，供 orchestrator 编排多 Agent 协作。
详见 ``engine.py`` 模块文档。
"""
from .engine import (
    WorkflowEngine,
    WorkflowNode,
    WorkflowResult,
    WorkflowStatus,
)

__all__ = [
    "WorkflowEngine",
    "WorkflowNode",
    "WorkflowResult",
    "WorkflowStatus",
]
