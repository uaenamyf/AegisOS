# date: 2026-07-04
# dev: myf
"""记忆压缩器模块。

当上下文中的记忆片段数量过多、估算 token 超过预算时，按"决策保留 +
最近保留 + 其余压缩为摘要"的策略对记忆进行压缩，以控制后续 LLM 调用
的输入长度。

压缩策略：
    1. 估算当前上下文 token 数；若未超预算则原样返回。
    2. 保留所有 ``decision`` 类记忆与 ``recent`` 为真的记忆（重要且新鲜）。
    3. 将剩余记忆合并为一条 ``digest`` 类摘要记忆，记录其原始 task_id 列表。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


def _token_estimate(ctx: list[MemoryPacket]) -> int:
    """粗略估算记忆上下文所占用的 token 数。

    采用"字符数 / 4"的经验规则进行估算（近似英文 1 token≈4 字符），
    汇总每条记忆的 summary、working、episodic 三个字段的字符长度。

    Args:
        ctx: 待估算的记忆片段列表。

    Returns:
        估算得到的 token 数（整数）。最小为 1，避免后续除零或预算判断为 0。
    """
    total = 0
    for m in ctx:
        # 同时累加三个文本字段的字符长度，None 会被 str() 转为 "None"
        total += len(str(m.summary)) + len(str(m.working)) + len(str(m.episodic))
    # 经验公式：约 4 个字符对应 1 个 token，+1 保证至少返回 1
    return total // 4 + 1


def compress(context: list[MemoryPacket], budget: int) -> list[MemoryPacket]:
    """在 token 预算内压缩记忆上下文。

    若当前上下文未超出预算则原样返回；否则保留决策类与最近记忆，
    并将其余记忆压缩为一条摘要（digest）记忆，从而在丢失细节的同时
    保留可追溯的 task_id 列表。

    Args:
        context: 原始记忆上下文列表。
        budget: 允许的最大 token 数（由调用方根据模型上下文窗口设定）。

    Returns:
        压缩后的记忆列表。可能包含：
            - 保留的原记忆（decision 或 recent）
            - 一条汇总了被压缩记忆的 digest 记忆（若有 rest）
        若未超预算则返回原列表引用。

    Raises:
        本函数不显式抛出异常。
    """
    # 1) 未超预算：无需压缩，直接返回原上下文
    if _token_estimate(context) <= budget:
        return context
    # 2) 保留重要记忆：决策类或标记为最近的记忆
    keep = [m for m in context if m.kind == "decision" or m.recent]
    # 3) 其余记忆作为待压缩集合；用 `not in` 判断保持原顺序
    rest = [m for m in context if m not in keep]
    # 4) 若没有可压缩记忆，则只返回保留集合
    if not rest:
        return keep
    # 5) 将待压缩记忆合并为一条摘要记忆，用 " | " 连接各条 summary（缺失时用 task_id 兜底）
    digest = MemoryPacket(
        task_id="digest",
        kind="digest",
        summary=" | ".join((m.summary or m.task_id) for m in rest),
        compression={
            "count": len(rest),  # 被压缩的记忆条数
            "ids": [m.task_id for m in rest],  # 原始 task_id 列表，便于溯源
        },
    )
    # 6) 保留集合 + 摘要记忆作为最终输出
    return keep + [digest]
