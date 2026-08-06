# date: 2026-07-05
# dev: myf
"""依赖注入（DI）组合根。

本模块是 AegisOS 后端的组合根（composition root），负责装配所有运行时依赖：
数据库引擎与仓储、11 个攻防 Agent 的模拟运行时、内存/执行/事件总线等
``agents.api`` 端口的占位实现，以及上层业务服务（Session/Task/Agent/Memory/Graph）。
同时通过 ``Annotated[...Depends(...)]`` 形式暴露 FastAPI 惯用的依赖别名，
供路由层直接注入。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

# date: 2026-08-01
# dev: 123 chen
# changelog: 导入 MemoryStore（v2 记忆系统，含 7 个新模块）
from aegisos_agents.memory.memory_store import MemoryStore
from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks import (
    MockAgentRegistry,
    MockEventBusAPI,
    MockExecutionAPI,
    MockRuntime,
)
from backend.mocks.cyber_provider import _CyberMockProvider
from backend.repositories.database import (
    configure_session_factory,
    create_engine,
    create_session_factory,
    init_db,
)
from backend.repositories.repositories import SessionRepository, TaskRepository
from backend.services.agent_service import AgentService
from backend.services.cyber_defense_service import CyberDefenseService
from backend.services.di_ports import (
    PersistencePortImpl,
    SessionPortImpl,
    TaskUpdatePortImpl,
)
from backend.services.graph_service import GraphService
from backend.services.memory_service import MemoryService
from backend.services.session_service import SessionService
from backend.services.task_service import TaskService

# date: 2026-08-06
# dev: czy
# changelog: 接入 data 层存储后端（默认 in_memory）
from data.api import create_graph_store, create_vector_store
from tooling.configs.settings import settings


class Composition:
    """依赖注入组合根，装配整个后端的运行时依赖。

    在构造时一次性创建并连接：数据库引擎与仓储、``agents.api`` 端口的 mock
    实现、上层业务服务，以及由后端实现的 DI 端口。进程内通过单例
    :func:`get_composition` 访问。

    Attributes:
        engine: SQLAlchemy 异步引擎。
        session_factory: 会话工厂，用于创建 DB 会话。
        session_repo: 会话仓储。
        task_repo: 任务仓储。
        agent_registry: Agent 注册表（mock）。
        runtime: Agent 运行时（mock，含攻防 Agent 调用）。
        orchestrator: SDK 攻防编排器（红蓝紫三条链），Mock / 真实模式共享实例。
        memory_api: 记忆 API（mock）。
        execution_api: 工具执行 API（mock）。
        event_bus: 事件总线（mock）。
        session_service: 会话服务。
        task_service: 任务服务。
        agent_service: Agent 服务。
        memory_service: 记忆服务。
        graph_service: 图服务。
        persistence_port: 持久化 DI 端口实现。
        session_port: 会话 DI 端口实现。
        task_update_port: 任务更新 DI 端口实现。
    """

    def __init__(self, database_url: str | None = None) -> None:
        # --- 持久化层 ---
        self.engine = create_engine(database_url) if database_url else create_engine()
        self.session_factory = create_session_factory(self.engine)
        configure_session_factory(self.session_factory)
        self.session_repo = SessionRepository(self.session_factory)
        self.task_repo = TaskRepository(self.session_factory)

        # --- Mock agents.api 实现（agents P5 未就绪） ---
        self.agent_registry = MockAgentRegistry()
        # date: 2026-08-06
        # dev: czy
        # changelog: MemoryStore 注入 data 层存储后端（默认 in_memory，真实库按配置启用）
        self.memory_api = MemoryStore(
            vector_backend=self._build_vector_backend(),
            graph_backend=self._build_graph_backend(),
        )
        self.execution_api = MockExecutionAPI()
        self.event_bus = MockEventBusAPI()

        # R4.7: 创建共享 CyberOrchestrator（Mock / 真实模式自动切换）
        self.orchestrator = self._create_orchestrator()

        # MockRuntime 注入共享 orchestrator，避免创建重复实例
        self.runtime = MockRuntime(orchestrator=self.orchestrator)

        # --- 服务层 ---
        self.session_service = SessionService(self.session_repo)
        self.task_service = TaskService(self.task_repo, self.runtime)
        self.agent_service = AgentService(self.agent_registry, self.runtime)
        self.memory_service = MemoryService(self.memory_api)
        self.graph_service = GraphService(self.event_bus)
        # R4.7: CyberDefenseService 注入共享 orchestrator
        self.cyber_defense_service = CyberDefenseService(orchestrator=self.orchestrator)

        # --- DI 端口（agents.api.ports）由后端实现 ---
        self.persistence_port = PersistencePortImpl(self.task_repo)
        self.session_port = SessionPortImpl(self.session_repo)
        self.task_update_port = TaskUpdatePortImpl(self.task_repo)

    @staticmethod
    def _build_vector_backend():
        """按 settings.storage 构造向量存储后端；in_memory 模式返回 None。

        Returns:
            VectorStoreAPI 实例或 None（使用记忆模块内置实现）。
        """
        s = settings.storage
        if s.vector_mode == "in_memory":
            return None
        return create_vector_store(
            s.vector_mode,
            url=s.qdrant_url,
            api_key=s.qdrant_api_key,
            collection=s.qdrant_collection,
        )

    @staticmethod
    def _build_graph_backend():
        """按 settings.storage 构造图存储后端；in_memory 模式返回 None。

        Returns:
            GraphStoreAPI 实例或 None（使用记忆模块内置实现）。
        """
        s = settings.storage
        if s.graph_mode == "in_memory":
            return None
        return create_graph_store(
            s.graph_mode,
            uri=s.neo4j_uri,
            user=s.neo4j_user,
            password=s.neo4j_password,
        )

    @staticmethod
    def _create_orchestrator() -> CyberOrchestrator:
        """创建 CyberOrchestrator 实例，根据运行模式自动选择 Mock / 真实 API。

        - Mock 模式（默认）：注入 ``_CyberMockProvider``，SDK Agent 走预置响应表
        - 真实 API 模式（``AEGIS_USE_MOCK=false`` + ``OPENAI_API_KEY``）：
          通过 ``SDKProvider.get_sdk_model()`` 注入 SDK ``OpenAIChatCompletionsModel``

        Returns:
            装配好的 :class:`CyberOrchestrator` 实例。
        """
        import os

        use_mock = os.getenv("AEGIS_USE_MOCK", "").lower()
        has_key = bool(os.getenv("OPENAI_API_KEY"))
        is_mock = use_mock in ("1", "true", "yes") or not has_key

        if is_mock:
            return CyberOrchestrator(mock=_CyberMockProvider())

        # 真实 API 模式
        from aegisos_agents.tools.llms.sdk_provider import SDKProvider

        provider = SDKProvider()
        model = provider.get_sdk_model()
        return CyberOrchestrator(model=model)

    async def startup(self) -> None:
        """启动阶段：初始化数据库（建表）。"""
        await init_db(self.engine)

    async def shutdown(self) -> None:
        """关闭阶段：释放数据库引擎连接池。"""
        await self.engine.dispose()


_composition: Composition | None = None


def get_composition() -> Composition:
    """返回进程级单例组合根。"""
    global _composition
    if _composition is None:
        _composition = Composition()
    return _composition


def reset_composition(database_url: str | None = None) -> Composition:
    """重建组合根（主要用于测试场景）。

    Args:
        database_url: 可选的数据库连接字符串，用于测试隔离。

    Returns:
        新建的 :class:`Composition` 实例。
    """
    global _composition
    _composition = Composition(database_url=database_url)
    return _composition


# --- FastAPI 依赖提供者 ---


def get_session_service() -> SessionService:
    """提供 SessionService 依赖。"""
    return get_composition().session_service


def get_task_service() -> TaskService:
    """提供 TaskService 依赖。"""
    return get_composition().task_service


def get_agent_service() -> AgentService:
    """提供 AgentService 依赖。"""
    return get_composition().agent_service


def get_memory_service() -> MemoryService:
    """提供 MemoryService 依赖。"""
    return get_composition().memory_service


def get_graph_service() -> GraphService:
    """提供 GraphService 依赖。"""
    return get_composition().graph_service


def get_cyber_defense_service() -> CyberDefenseService:
    """提供 CyberDefenseService 依赖。"""
    return get_composition().cyber_defense_service


def get_event_bus() -> MockEventBusAPI:
    """提供 EventBus 依赖。"""
    return get_composition().event_bus


def get_execution_api() -> MockExecutionAPI:
    """提供 ExecutionAPI 依赖。"""
    return get_composition().execution_api


# --- Annotated 依赖别名（FastAPI 惯用 DI 写法，避免 B008 告警） ---

SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
EventBusDep = Annotated[MockEventBusAPI, Depends(get_event_bus)]
ExecutionApiDep = Annotated[MockExecutionAPI, Depends(get_execution_api)]
