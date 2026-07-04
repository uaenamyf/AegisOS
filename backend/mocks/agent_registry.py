# date: 2026-07-05
# dev: myf
# changelog: 从 composition.py 拆出 MockAgentRegistry + _CYBER_AGENT_SPECS + _make_cyber_agent
"""MockAgentRegistry — agents.api.AgentRegistryAPI 的内存占位实现。"""

from __future__ import annotations

from typing import Any

from protocol import Agent, AgentStatus, NodeRef

# ---------------------------------------------------------------------------
# 攻防 Agent 元数据定义
# 每个 spec 描述一个攻防 Agent 的 id、显示名、角色与能力标签，供 _make_cyber_agent
# 转换为 protocol.Agent 数据类并注册到 MockAgentRegistry。
# ---------------------------------------------------------------------------

_CYBER_AGENT_SPECS: list[dict[str, Any]] = [
    {
        "agent_id": "recon",
        "name": "Recon Agent",
        "role": "recon",
        "capabilities": ["asset-discovery", "port-scan", "service-fingerprint"],
    },
    {
        "agent_id": "vuln_correlator",
        "name": "Vulnerability Correlator",
        "role": "vuln_correlator",
        "capabilities": ["cve-correlation", "cvss-scoring", "attack-surface-mapping"],
    },
    {
        "agent_id": "exploit_planner",
        "name": "Exploit Planner",
        "role": "exploit_planner",
        "capabilities": ["exploit-chain", "attack-graph", "kill-chain"],
    },
    {
        "agent_id": "lateral_move",
        "name": "Lateral Movement Planner",
        "role": "lateral_move",
        "capabilities": ["lateral-movement", "privilege-escalation", "pivot"],
    },
    {
        "agent_id": "detector",
        "name": "Detector Agent",
        "role": "detector",
        "capabilities": ["intrusion-detection", "anomaly-detection", "alerting"],
    },
    {
        "agent_id": "triage",
        "name": "Triage Agent",
        "role": "triage",
        "capabilities": ["alert-triage", "deduplication", "prioritization"],
    },
    {
        "agent_id": "threat_hunt",
        "name": "Threat Hunter",
        "role": "threat_hunt",
        "capabilities": ["threat-hunting", "hypothesis-generation", "attck-mapping"],
    },
    {
        "agent_id": "ir_planner",
        "name": "IR Planner",
        "role": "ir_planner",
        "capabilities": ["incident-response", "containment", "rollback-planning"],
    },
    {
        "agent_id": "forensics",
        "name": "Forensics Agent",
        "role": "forensics",
        "capabilities": ["digital-forensics", "root-cause-analysis", "timeline-reconstruction"],
    },
    {
        "agent_id": "critic",
        "name": "Critic Agent",
        "role": "critic",
        "capabilities": ["adversarial-critique", "red-blue-validation", "attck-compliance"],
    },
    {
        "agent_id": "reviewer-defense",
        "name": "Consistency Reviewer",
        "role": "reviewer",
        "capabilities": ["consistency-review", "artifact-validation", "cross-check"],
    },
]


def _make_cyber_agent(spec: dict[str, Any]) -> Agent:
    """根据 spec 字典构建 protocol ``Agent`` 数据类。

    Args:
        spec: 攻防 Agent 元数据，须包含 ``agent_id``、``name``、``role``、
            ``capabilities`` 字段。

    Returns:
        初始状态为 ``Idle`` 的 :class:`protocol.Agent` 实例。
    """
    aid = spec["agent_id"]
    return Agent(
        agent_id=aid,
        name=spec["name"],
        role=spec["role"],
        ref=NodeRef(aid, "agent", spec["name"]),
        capabilities=spec["capabilities"],
        status=AgentStatus.Idle,
    )


class MockAgentRegistry:
    """``agents.api.AgentRegistryAPI`` 的占位实现，返回预设的 Agent 列表。

    内置 3 个通用 Agent（coder/reviewer/researcher）与 11 个攻防 Agent。
    攻防 Agent 元数据来自 :data:`_CYBER_AGENT_SPECS`。

    Attributes:
        _agents: ``agent_id -> Agent`` 的内存索引表。
    """

    def __init__(self) -> None:
        # 3 个通用 Agent。
        self._agents: dict[str, Agent] = {
            "coder": Agent(
                agent_id="coder",
                name="Coder",
                role="coder",
                ref=NodeRef("coder", "agent", "Coder"),
                capabilities=["code", "debug", "test"],
                status=AgentStatus.Idle,
            ),
            "reviewer": Agent(
                agent_id="reviewer",
                name="Reviewer",
                role="reviewer",
                ref=NodeRef("reviewer", "agent", "Reviewer"),
                capabilities=["review", "critique"],
                status=AgentStatus.Idle,
            ),
            "researcher": Agent(
                agent_id="researcher",
                name="Researcher",
                role="researcher",
                ref=NodeRef("researcher", "agent", "Researcher"),
                capabilities=["search", "summarize"],
                status=AgentStatus.Idle,
            ),
        }
        # 11 个攻防 Agent，由 spec 列表批量构建。
        for spec in _CYBER_AGENT_SPECS:
            agent = _make_cyber_agent(spec)
            self._agents[agent.agent_id] = agent

    def register(self, agent: Agent) -> None:
        """注册或覆盖一个 Agent。"""
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> Agent:
        """按 id 查询 Agent。

        Args:
            agent_id: Agent 唯一标识。

        Returns:
            对应的 :class:`Agent` 实例。

        Raises:
            KeyError: 当 ``agent_id`` 不存在时抛出。
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        return agent

    def list_agents(self) -> list[Agent]:
        """返回所有已注册 Agent 的列表。"""
        return list(self._agents.values())
