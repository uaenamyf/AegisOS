# date: 2026-07-05
# dev: myf
"""Mock 实现层。

从 ``backend/core/composition.py`` 拆分而来，集中放置 ``agents.api`` 各端口的
内存占位实现，使组合根聚焦于"装配"而非"实现"。
"""

from backend.mocks.agent_registry import _CYBER_AGENT_SPECS, MockAgentRegistry, _make_cyber_agent
from backend.mocks.cyber_provider import _build_cyber_mock_responses, _CyberMockProvider
from backend.mocks.event_bus import MockEventBusAPI
from backend.mocks.execution import MockExecutionAPI
from backend.mocks.memory import MockMemoryAPI
from backend.mocks.runtime import MockRuntime

__all__ = [
    "MockAgentRegistry",
    "MockRuntime",
    "MockMemoryAPI",
    "MockExecutionAPI",
    "MockEventBusAPI",
    "_CyberMockProvider",
    "_build_cyber_mock_responses",
    "_CYBER_AGENT_SPECS",
    "_make_cyber_agent",
]
