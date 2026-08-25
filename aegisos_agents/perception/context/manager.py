# date: 2026-08-01
# dev: 123 chen
"""上下文管理器 —— 会话上下文生命周期管理。

管理 Agent 会话上下文的打开/关闭/打包/切换/隔离，
绑定 :class:`MemoryStore` 的工作记忆层，按 token 预算裁剪上下文。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aegisos_agents.perception.context.window import TokenBudget

if TYPE_CHECKING:
    from aegisos_agents.memory.memory_store import MemoryStore


@dataclass
class Context:
    """会话上下文快照。

    Attributes:
        session_id: 所属会话标识符。
        working_packets: 裁剪后的工作记忆列表。
        token_usage: 实际 token 使用量。
        budget_remaining: 剩余 token 预算。
        truncated: 是否发生过裁剪。
    """

    session_id: str = ""
    working_packets: list = field(default_factory=list)
    token_usage: int = 0
    budget_remaining: int = 0
    truncated: bool = False


class ContextManager:
    """会话上下文生命周期管理器。

    绑定 :class:`MemoryStore` 的工作记忆层与 :class:`TokenBudget` 的裁剪能力，
    提供会话上下文的打开、关闭、打包、切换、隔离操作。

    Attributes:
        _budget: Token 预算管理器。
        _store: MemoryStore 引用（只读 working 层）。
        _active_session: 当前活跃的会话 ID。
        _contexts: {session_id -> Context} 缓存。
    """

    def __init__(self, memory_store: MemoryStore | None = None) -> None:
        """初始化上下文管理器。

        Args:
            memory_store: MemoryStore 引用，为 None 时后续通过 ``open()`` 传入。
        """
        self._budget = TokenBudget()
        self._store = memory_store
        self._active_session: str = ""
        self._contexts: dict[str, Context] = {}

    # ---- 生命周期 ----

    def open(
        self, session_id: str, memory_store: MemoryStore | None = None
    ) -> Context:
        """打开一个会话上下文。

        Args:
            session_id: 会话唯一标识。
            memory_store: MemoryStore 引用，若构造时未传入则在此处绑定。

        Returns:
            初始化的空 Context（仅有 session_id）。
        """
        if memory_store is not None:
            self._store = memory_store
        self._active_session = session_id
        ctx = Context(session_id=session_id)
        self._contexts[session_id] = ctx
        return ctx

    def close(self, session_id: str) -> None:
        """关闭会话上下文并清理本地缓存。

        不清理 MemoryStore 的工作记忆（由 ``MemoryStore.end_session`` 负责）。

        Args:
            session_id: 待关闭的会话标识符。
        """
        self._contexts.pop(session_id, None)
        if self._active_session == session_id:
            self._active_session = ""

    # ---- 打包 ----

    def pack(self, session_id: str, budget: int = 4096) -> Context:
        """打包会话上下文：从工作记忆拉取 → token 裁剪 → 返回 Context。

        Args:
            session_id: 目标会话标识符。
            budget: token 预算上限，默认 4096。

        Returns:
            打包后的 Context，含裁剪后的 working_packets 与统计信息。
        """
        if self._store is None:
            return Context(session_id=session_id)
        raw = self._store.working.get(session_id)
        trimmed = self._budget.trim(raw, budget)
        usage = self._budget.estimate_packets(trimmed)
        ctx = Context(
            session_id=session_id,
            working_packets=trimmed,
            token_usage=usage,
            budget_remaining=max(budget - usage, 0),
            truncated=len(trimmed) < len(raw),
        )
        self._contexts[session_id] = ctx
        return ctx

    # ---- 切换 ----

    def switch(self, from_sid: str, to_sid: str) -> Context:
        """切换会话上下文：保存当前会话 → 加载目标会话。

        Args:
            from_sid: 当前会话标识符。
            to_sid: 目标会话标识符。

        Returns:
            目标会话的 Context（调用 pack 生成）。
        """
        # 打包当前会话上下文（保存状态）
        self.pack(from_sid)
        # 切换到目标会话
        self._active_session = to_sid
        return self.pack(to_sid)

    # ---- 隔离 ----

    def isolate(self, session_id: str) -> Context | None:
        """隔离单个会话的完整上下文快照。

        不受其他会话影响，返回该会话的独立 Context。

        Args:
            session_id: 目标会话标识符。

        Returns:
            该会话的 Context；无工作记忆时返回 None。
        """
        if self._store is None:
            return self._contexts.get(session_id)
        raw = self._store.working.get(session_id)
        if not raw:
            return None
        ctx = Context(
            session_id=session_id,
            working_packets=list(raw),
            token_usage=self._budget.estimate_packets(raw),
            budget_remaining=0,
            truncated=False,
        )
        return ctx
