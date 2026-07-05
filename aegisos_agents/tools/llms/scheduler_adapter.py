# date: 2026-07-04
# dev: myf
# changelog: Scheduler adapter for LLM routing
"""调度器适配器：为 LLM 路由层暴露调度能力。

本模块提供一个薄封装函数 :func:`schedule_for_llm`，将
``agents.planning.engine.scheduler`` 的调度能力暴露给
``agents.tools.llms`` 的消费者，使其无需直接依赖 ``agents.planning``
模块，降低模块间耦合。
"""

from __future__ import annotations

from aegisos_agents.planning.engine.scheduler.scheduler import Model, schedule
from protocol.scheduler import Task


def schedule_for_llm(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    """薄适配层：委托给 ``engine.scheduler.schedule()``。

    存在目的是让 ``agents.tools.llms`` 的消费者不必直接依赖
    ``agents.planning``，统一从此处获取调度结果。

    Args:
        task: 待调度的任务对象，含优先级、能力需求等元信息。
        models: 候选模型列表，调度器从中选择最合适的一个。
        required_capability: 任务要求的特定能力名（如 ``"reasoning"``）；
            为 ``None`` 表示不强制能力约束。

    Returns:
        调度器选定的 :class:`Model` 实例。

    Raises:
        可能向上抛出 ``schedule()`` 内部异常（如无可用模型）。
    """
    return schedule(task, models, required_capability=required_capability)
