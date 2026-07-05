# date: 2026-06-27
# dev: myf
# changelog: 重构 agents/api，移除 PlanningAPI 和 PerceptionAPI（内聚为域内部），仅保留外部真正需要的 5 个接口
"""智能体域公共接口包 —— 面向其他域的最小外部接口集合。

本模块仅暴露其他域（主要是 backend）合法调用的接口；智能体域内部的认知能力
（规划 planning / 感知 perception）不在此暴露。后端通过 ``RuntimeAPI.submit(task)``
提交任务，智能体域内部自行完成 规划→路由→调度→执行→反思 的闭环。

详见 ``developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md`` §3.1。

对外暴露（5 个核心接口）：
    AgentRegistryAPI · RuntimeAPI · MemoryAPI · EventBusAPI · ExecutionAPI

域内部接口（不在此暴露）：
    PlanningAPI（agents/planning/engine/）· PerceptionAPI（agents/perception/）
"""

from __future__ import annotations

from typing import Any, Protocol

from protocol import (  # 跨域数据契约，禁自造并行结构（见 03_IMPORT_SPEC）
    Agent,
    Event,
    Heartbeat,
    MemoryPacket,
    Task,
    ToolCall,
    ToolResult,
)

from .ports import PersistencePort, SessionPort, TaskUpdatePort  # DI 端口，由后端实现并注入


class AgentRegistryAPI(Protocol):
    """智能体注册表接口，提供智能体的注册、查询与枚举能力。

        后端可通过此接口查询当前可用的智能体集合，用于任务派发决策。
    n    Attributes:
            无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def register(self, agent: Agent) -> None:
        """注册一个智能体到注册表。

        Args:
            agent: 待注册的智能体实例，见 ``protocol.Agent``。
        """
        ...

    def get(self, agent_id: str) -> Agent:
        """按标识符获取智能体。

        Args:
            agent_id: 智能体唯一标识符。

        Returns:
            Agent: 对应的智能体实例。

        Raises:
            KeyError: 当 ``agent_id`` 不存在时由实现抛出。
        """
        ...

    def list_agents(self) -> list[Agent]:
        """枚举所有已注册的智能体。

        Returns:
            list[Agent]: 当前注册表中的智能体列表。
        """
        ...


class MemoryAPI(Protocol):
    """记忆子系统接口，提供智能体记忆的读取、写入与检索能力。

    该接口对应 ``agents/memory`` 域，后端可用于记忆初始化或诊断查询。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def read(self, query: dict) -> MemoryPacket:
        """按查询条件读取记忆。

        Args:
            query: 查询条件字典，由记忆子系统定义具体键含义。

        Returns:
            MemoryPacket: 匹配的记忆数据包。
        """
        ...

    def write(self, packet: MemoryPacket) -> bool:
        """写入一条记忆。

        Args:
            packet: 待写入的记忆数据包。

        Returns:
            bool: 写入成功返回 ``True``，失败返回 ``False``。
        """
        ...

    def retrieve(self, query: dict) -> list:
        """按查询条件检索相关记忆条目（语义检索）。

        Args:
            query: 检索条件字典，通常包含语义向量或关键词。

        Returns:
            list: 匹配的记忆条目列表，具体元素类型由实现决定。
        """
        ...


class ExecutionAPI(Protocol):
    """工具执行接口，提供智能体调用外部工具的能力。

    后端在需要直接调用工具（绕过完整 runtime 编排）时可使用此接口；
    正常任务流程由 ``RuntimeAPI`` 统一编排，工具调用在其内部发生。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def execute(self, call: ToolCall) -> ToolResult:
        """执行一次工具调用。

        Args:
            call: 工具调用描述，见 ``protocol.ToolCall``。

        Returns:
            ToolResult: 工具执行结果，见 ``protocol.ToolResult``。

        Raises:
            ToolExecutionError: 当工具执行失败时由实现抛出（具体异常类型由实现定义）。
        """
        ...


class EventBusAPI(Protocol):
    """事件总线接口，提供事件发布与订阅能力。

    事件总线是跨模块低熵通信的核心通道，遵循 ``04_PROTOCOL_SPEC`` §16
    的稀疏路由约束。后端可订阅事件以驱动 UI 推送与状态同步。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def publish(self, event: Event) -> None:
        """发布一个事件到事件总线。

        事件将按稀疏路由规则投递给相关订阅者，非全广播。

        Args:
            event: 待发布事件，见 ``protocol.Event``。
        """
        ...

    def subscribe(self, topic: str, handler) -> None:
        """订阅指定主题的事件。

        Args:
            topic: 事件主题，订阅者据此过滤事件。
            handler: 事件处理回调函数，签名为 ``handler(event: Event) -> None``。
        """
        ...


class RuntimeAPI(Protocol):
    """运行时接口，智能体域的核心入口，负责任务提交与智能体生命周期管理。

    后端通过 ``submit`` 提交任务（不指定具体智能体，由内部规划路由分配），
    或通过 ``run`` 指定智能体执行任务。同时提供停止与心跳查询能力。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def submit(self, task: Task) -> Task:
        """提交任务到运行时，由内部规划-路由-调度自动分配智能体执行。

        Args:
            task: 待执行任务，见 ``protocol.Task``。

        Returns:
            Task: 带有分配信息（如 agent_id）的任务对象。
        """
        ...

    def run(self, agent_id: str, task: Task) -> Any:
        """指定智能体执行任务并返回执行结果。

        Args:
            agent_id: 目标智能体标识符。
            task: 待执行任务。

        Returns:
            Any: 智能体执行结果，具体类型由任务与智能体决定。

        Raises:
            AgentNotFound: 当 ``agent_id`` 不存在时由实现抛出。
        """
        ...

    def stop(self, agent_id: str) -> bool:
        """停止指定智能体的当前执行。

        Args:
            agent_id: 目标智能体标识符。

        Returns:
            bool: 停止成功返回 ``True``，智能体未运行或已停止返回 ``False``。
        """
        ...

    def heartbeat(self, agent_id: str) -> Heartbeat:
        """查询智能体心跳状态。

        Args:
            agent_id: 目标智能体标识符。

        Returns:
            Heartbeat: 心跳信息，见 ``protocol.Heartbeat``，包含状态与时间戳。

        Raises:
            AgentNotFound: 当 ``agent_id`` 不存在时由实现抛出。
        """
        ...


__all__ = [  # 对外暴露的公共接口清单
    "AgentRegistryAPI",
    "MemoryAPI",
    "ExecutionAPI",
    "EventBusAPI",
    "RuntimeAPI",
    "PersistencePort",
    "SessionPort",
    "TaskUpdatePort",
]
