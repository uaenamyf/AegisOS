# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 超长程记忆唤醒机制
from __future__ import annotations

from protocol.memory import MemoryPacket

TOP_K = 5


def recall(
    trigger: str,
    episodic: list[MemoryPacket],
    vector: list[MemoryPacket],
) -> list[MemoryPacket]:
    trigger_lower = trigger.lower()
    candidates: list[MemoryPacket] = []

    for m in episodic:
        if trigger_lower in (m.summary or "").lower():
            candidates.append(m)

    for m in vector:
        if trigger_lower in (m.summary or "").lower():
            candidates.append(m)

    decisions = [m for m in candidates if m.kind == "decision"]
    normals = [m for m in candidates if m.kind != "decision"]
    return (decisions + normals)[:TOP_K]
