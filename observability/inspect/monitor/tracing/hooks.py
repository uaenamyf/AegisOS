# date: 2026-07-07
# dev: myf
"""SDK AgentHooks 实现 —— 记录 Agent 生命周期事件到结构化日志。

本模块实现 :class:`CyberAgentHooks`，继承 SDK ``AgentHooksBase``，
在 Agent 的 ``on_start`` / ``on_end`` / ``on_handoff`` / ``on_tool_start`` /
``on_tool_end`` / ``on_llm_start`` / ``on_llm_end`` 回调中记录事件。

使用方式::

    hooks = CyberAgentHooks(agent_name="ReconAgent")
    agent.hooks = hooks
    # SDK Runner 运行该 Agent 时自动回调

    events = hooks.events  # 获取采集的事件列表

设计决策：
    - 所有回调为 ``async``（SDK 要求）
    - 事件记录到内存列表，不写文件（由调用方决定持久化）
    - ``reset()`` 方法清空事件列表
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from agents.lifecycle import AgentHooksBase


# date: 2026-07-07
# dev: myf
# changelog: 新建 CyberAgentHooks + HookEvent


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
    """Agent 生命周期钩子 —— 采集 Agent 各阶段事件。

    设置到 SDK ``Agent.hooks`` 属性后，SDK Runner 在执行该 Agent 时
    会自动调用对应回调方法，将事件记录到 :attr:`events` 列表。

    Attributes:
        agent_name: 绑定的 Agent 名称。
        events: 采集的事件列表。
    """

    def __init__(self, agent_name: str = "") -> None:
        """初始化钩子。

        Args:
            agent_name: 绑定的 Agent 名称（用于事件标记）。
        """
        self.agent_name = agent_name
        self.events: list[HookEvent] = []

    def reset(self) -> None:
        """清空事件列表。"""
        self.events.clear()

    async def on_start(self, context: Any, agent: Any) -> None:
        """Agent 开始执行前回调。"""
        name = getattr(agent, "name", self.agent_name)
        self.events.append(
            HookEvent(
                event_type="on_start",
                agent_name=name,
                data={"instructions": getattr(agent, "instructions", None)},
            )
        )

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
        self.events.append(
            HookEvent(
                event_type="on_end",
                agent_name=name,
                data={"output": output_data},
            )
        )

    async def on_handoff(
        self, context: Any, agent: Any, source: Any
    ) -> None:
        """Agent 被 handoff 到时回调。"""
        name = getattr(agent, "name", self.agent_name)
        source_name = getattr(source, "name", "unknown")
        self.events.append(
            HookEvent(
                event_type="on_handoff",
                agent_name=name,
                data={"source": source_name},
            )
        )

    async def on_tool_start(
        self, context: Any, agent: Any, tool: Any
    ) -> None:
        """工具开始执行前回调。"""
        name = getattr(agent, "name", self.agent_name)
        tool_name = getattr(tool, "name", str(tool))
        self.events.append(
            HookEvent(
                event_type="on_tool_start",
                agent_name=name,
                data={"tool": tool_name},
            )
        )

    async def on_tool_end(
        self, context: Any, agent: Any, tool: Any, result: object
    ) -> None:
        """工具执行完成后回调。"""
        name = getattr(agent, "name", self.agent_name)
        tool_name = getattr(tool, "name", str(tool))
        result_str = str(result)[:500] if result is not None else "None"
        self.events.append(
            HookEvent(
                event_type="on_tool_end",
                agent_name=name,
                data={"tool": tool_name, "result": result_str},
            )
        )

    async def on_llm_start(
        self,
        context: Any,
        agent: Any,
        system_prompt: str | None,
        input_items: list[Any],
    ) -> None:
        """LLM 调用前回调。"""
        name = getattr(agent, "name", self.agent_name)
        self.events.append(
            HookEvent(
                event_type="on_llm_start",
                agent_name=name,
                data={
                    "system_prompt_length": len(system_prompt) if system_prompt else 0,
                    "input_count": len(input_items) if input_items else 0,
                },
            )
        )

    async def on_llm_end(
        self, context: Any, agent: Any, response: Any
    ) -> None:
        """LLM 响应后回调。"""
        name = getattr(agent, "name", self.agent_name)
        self.events.append(
            HookEvent(
                event_type="on_llm_end",
                agent_name=name,
                data={"response_type": type(response).__name__},
            )
        )
