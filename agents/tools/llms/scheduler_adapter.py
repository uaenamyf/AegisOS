# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: Scheduler adapter for LLM routing
from __future__ import annotations

from agents.planning.engine.scheduler.scheduler import Model, schedule
from protocol.scheduler import Task


def schedule_for_llm(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    """Thin adapter: delegates to engine.scheduler.schedule().
    Exists so agents.tools.llms consumers don't depend on agents.planning directly.
    """
    return schedule(task, models, required_capability=required_capability)
