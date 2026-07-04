# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 超长程记忆唤醒机制
"""记忆回忆器模块。

提供基于触发词（trigger）的关键词匹配回忆能力。从情景记忆（episodic）和
向量记忆（vector）两个来源中检索与触发词相关的 MemoryPacket，并按
"决策优先"原则排序后截取 Top-K 返回。

模块定位：
    - 输入：触发字符串 + 两类记忆列表
    - 输出：与触发词相关的、决策优先的记忆片段列表
    - 特点：纯关键词子串匹配（大小写不敏感），不依赖向量相似度模型
"""

from __future__ import annotations

from protocol.memory import MemoryPacket

# 单次回忆返回的记忆数量上限，避免上下文过长
TOP_K = 5


def recall(
    trigger: str,
    episodic: list[MemoryPacket],
    vector: list[MemoryPacket],
) -> list[MemoryPacket]:
    """根据触发词从情景记忆与向量记忆中回忆相关记忆片段。

    匹配策略为大小写不敏感的子串匹配：只要某条记忆的 summary 中包含触发词，
    即视为命中。命中的记忆会先按类别排序（decision 优先），再截取 Top-K。

    Args:
        trigger: 触发回忆的关键词或短语，例如任务标题、用户指令片段。
        episodic: 情景记忆列表，通常记录历史交互过程中产生的显式记忆。
        vector: 向量记忆列表，通常为经过向量化检索后的候选记忆集合。

    Returns:
        与触发词匹配的记忆片段列表，长度不超过 ``TOP_K``。列表顺序为
        ``decisions`` 在前、其余命中记忆在后，整体截取前 ``TOP_K`` 条。

    Raises:
        本函数不显式抛出异常；若传入 None 触发词需由调用方保证
        （summary 字段为空时已通过 ``or ""`` 兜底）。
    """
    # 统一转小写，保证后续子串匹配大小写不敏感
    trigger_lower = trigger.lower()
    candidates: list[MemoryPacket] = []

    # 1) 在情景记忆中做子串匹配，命中即加入候选集
    for m in episodic:
        # summary 可能为 None，用空串兜底避免 AttributeError
        if trigger_lower in (m.summary or "").lower():
            candidates.append(m)

    # 2) 在向量记忆中做同样的子串匹配
    for m in vector:
        if trigger_lower in (m.summary or "").lower():
            candidates.append(m)

    # 3) 决策类记忆优先排前，保证关键历史决策不被截断
    decisions = [m for m in candidates if m.kind == "decision"]
    normals = [m for m in candidates if m.kind != "decision"]
    # 决策优先拼接后截取 Top-K，超出部分丢弃
    return (decisions + normals)[:TOP_K]
