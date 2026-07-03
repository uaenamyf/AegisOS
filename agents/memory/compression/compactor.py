# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 超长程上下文压缩
from __future__ import annotations

from protocol.memory import MemoryPacket


def _token_estimate(ctx: list[MemoryPacket]) -> int:
    total = 0
    for m in ctx:
        total += len(str(m.summary)) + len(str(m.working)) + len(str(m.episodic))
    return total // 4 + 1


def compress(context: list[MemoryPacket], budget: int) -> list[MemoryPacket]:
    if _token_estimate(context) <= budget:
        return context
    keep = [m for m in context if m.kind == "decision" or m.recent]
    rest = [m for m in context if m not in keep]
    if not rest:
        return keep
    digest = MemoryPacket(
        task_id="digest",
        kind="digest",
        summary=" | ".join((m.summary or m.task_id) for m in rest),
        compression={
            "count": len(rest),
            "ids": [m.task_id for m in rest],
        },
    )
    return keep + [digest]
