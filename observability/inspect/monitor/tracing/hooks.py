# date: 2026-07-07
# dev: myf
# changelog: R5.4 AgentHooks 发布事件到 EventBus——回调中除记录到内存列表，还发布 protocol.Event 到总线
"""SDK AgentHooks 实现 —— 记录 Agent 生命周期事件到结构化日志 + 发布到 EventBus。

本模块实现 :class:`CyberAgentHooks`，继承 SDK ``AgentHooksBase``，
在 Agent 的 ``on_start`` / ``on_end`` / ``on_handoff`` / ``on_tool_start`` /
``on_tool_end`` / ``on_llm_start`` / ``on_llm_end`` 回调中记录事件。

R5.4 增强：可选注入 :class:`EventBus`，回调中除记录到 ``events`` 列表，
还发布对应 :class:`protocol.event.EventType` 事件到总线，供 ``observability/inspect/replay/``
回放与 ``backend/routers/sse.py`` 实时推送消费。

事件映射：
    - ``on_start`` → :attr:`EventType.AgentStart`
    - ``on_end`` → :attr:`EventType.AgentFinish`
    - ``on_tool_start`` → :attr:`EventType.ToolCall`
    - ``on_tool_end`` → :attr:`EventType.ToolFinish`

使用方式::

    # 无 EventBus（纯记录，向后兼容）
    hooks = CyberAgentHooks(agent_name="ReconAgent")

    # 有 EventBus（记录 + 发布，R5.4）
    hooks = CyberAgentHooks(agent_name="ReconAgent", eventbus=bus)

设计决策：
    - 所有回调为 ``async``（SDK 要求）
    - 事件记录到内存列表，不写文件（由调用方决定持久化）
    - ``reset()`` 方法清空事件列表
    - EventBus 为可选依赖（None 时不发布，保持向后兼容）
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agents.lifecycle import AgentHooksBase

if TYPE_CHECKING:
    from aegisos_agents.planning.engine.eventbus import EventBus


# date: 2026-07-07
# dev: myf
# changelog: 新建 CyberAgentHooks + HookEvent；R5.4 加 eventbus 发布


@dataclass
class HookEvent:
    """单个 Agent 生命周期事件。

    Attributes:
        event_type: 事件类型（``on_start`` / ``on_end`` / ``on_handoff`` /
            ``on_tool_start`` / ``on_tool_end`` / ``on_llm_start`` / ``on_llm_end``）。
        agent_name: 触发事件的 Agent 名称。
        timestamp: 事件时间戳。
        data: 事件附加数据（如 output / tool / response 等）。
    """

    event_type: str
    agent_name: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典。"""
        return {
            "event_type": self.event_type,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class CyberAgentHooks(AgentHooksBase):
    """Agent 生命周期钩子 —— 采集 Agent 各阶段事件 + 可选发布到 EventBus。

    设置到 SDK ``Agent.hooks`` 属性后，SDK Runner 在执行该 Agent 时
    会自动调用对应回调方法，将事件记录到 :attr:`events` 列表。
    R5.4：若注入 ``eventbus``，回调中还发布 :class:`protocol.Event` 到总线。

    Attributes:
        agent_name: 绑定的 Agent 名称。
        events: 采集的事件列表。
        eventbus: 可选的 :class:`EventBus` 实例；非 None 时发布事件到总线。
        task_id: 可选的任务 ID，作为发布事件的 ``task_id`` 字段。
    """

    def __init__(
        self,
        agent_name: str = "",
        eventbus: "EventBus | None" = None,
        task_id: str = "",
    ) -> None:
        """初始化钩子。

        Args:
            agent_name: 绑定的 Agent 名称（用于事件标记）。
            eventbus: 可选的 :class:`EventBus`；非 None 时回调中发布事件。
            task_id: 可选的任务 ID，作为发布事件的 ``task_id`` 字段。
        """
        self.agent_name = agent_name
        self.events: list[HookEvent] = []
        self.eventbus = eventbus
        self.task_id = task_id

    def reset(self) -> None:
        """清空事件列表。"""
        self.events.clear()

    def _publish(self, event_type: Any, data: dict[str, Any]) -> None:
        """发布事件到 EventBus（若注入）。

        Args:
            event_type: :class:`protocol.event.EventType` 枚举值。
            data: 事件负载。
        """
        if self.eventbus is None:
            return
        from protocol.event import Event
        from protocol.message import NodeRef

        event = Event(
            event_type=event_type,
            task_id=self.task_id,
            source=NodeRef(self.agent_name, "agent", self.agent_name),
            payload=data,
        )
        self.eventbus.publish(event)

    async def on_start(self, context: Any, agent: Any) -> None:
        """Agent 开始执行前回调。"""
        name = getattr(agent, "name", self.agent_name)
        data = {"instructions": getattr(agent, "instructions", None)}
        self.events.append(
            HookEvent(event_type="on_start", agent_name=name, data=data)
        )
        from protocol.event import EventType

        self._publish(EventType.AgentStart, data)

    async def on_end(self, context: Any, agent: Any, output: Any) -> None:
        """Agent 产出最终输出后回调。"""
        name = getattr(agent, "name", self.agent_name)
        output_data: Any
        if hasattr(output, "model_dump"):
            output_data = output.model_dump()
        elif isinstance(output, (str, int, float, bool)):
            output_data = output
        else:
            output_data = str(output)
        data = {"output": output_data}
        self.events.append(
            HookEvent(event_type="on_end", agent_name=name, data=data)
        )
        from protocol.event import EventType

        self._publish(EventType.AgentFinish, data)

    async def on_handoff(
        self, context: Any, agent: Any, source: Any
    ) -> None:
        """Agent 被 handoff 到时回调。"""
        name = getattr(agent, "name", self.agent_name)
        source_name = getattr(source, "name", "unknown")
        data = {"source": source_name}
        self.events.append(
            HookEvent(event_type="on_handoff", agent_name=name, data=data)
        )
        # handoff 无直接对应 EventType，用 AgentStart 表示新 Agent 接管
        from protocol.event import EventType

        self._publish(EventType.AgentStart, data)

    async def on_tool_start(
        self, context: Any, agent: Any, tool: Any
    ) -> None:
        """工具开始执行前回调。"""
        name = getattr(agent, "name", self.agent_name)
        tool_name = getattr(tool, "name", str(tool))
        data = {"tool": tool_name}
        self.events.append(
            HookEvent(event_type="on_tool_start", agent_name=name, data=data)
        )
        from protocol.event import EventType

        self._publish(EventType.ToolCall, data)

    async def on_tool_end(
        self, context: Any, agent: Any, tool: Any, result: object
    ) -> None:
        """工具执行完成后回调。"""
        name = getattr(agent, "name", self.agent_name)
        tool_name = getattr(tool, "name", str(tool))
        result_str = str(result)[:500] if result is not None else "None"
        data = {"tool": tool_name, "result": result_str}
        self.events.append(
            HookEvent(event_type="on_tool_end", agent_name=name, data=data)
        )
        from protocol.event import EventType

        self._publish(EventType.ToolFinish, data)

    async def on_llm_start(
        self,
        context: Any,
        agent: Any,
        system_prompt: str | None,
        input_items: list[Any],
    ) -> None:
        """LLM 调用前回调。"""
        name = getattr(agent, "name", self.agent_name)
        data = {
            "system_prompt_length": len(system_prompt) if system_prompt else 0,
            "input_count": len(input_items) if input_items else 0,
        }
        self.events.append(
            HookEvent(event_type="on_llm_start", agent_name=name, data=data)
        )
        # LLM 调用无直接对应 EventType，不发布（避免噪声）

    async def on_llm_end(
        self, context: Any, agent: Any, response: Any
    ) -> None:
        """LLM 响应后回调。"""
        name = getattr(agent, "name", self.agent_name)
        data = {"response_type": type(response).__name__}
        self.events.append(
            HookEvent(event_type="on_llm_end", agent_name=name, data=data)
        )
        # LLM 响应无直接对应 EventType，不发布（避免噪声）
