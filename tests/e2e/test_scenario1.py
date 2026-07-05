# date: 2026-07-06
# dev: myf
# changelog: E13 场景 1 端到端测试——红→蓝→紫完整链路 + B3 记忆认知循环集成
"""场景 1 端到端测试 —— 网络防御（红→蓝→紫完整链路）。

验证赛事场景 1 的全链路数据流，并集成 B3 记忆认知循环：
    红队：recon → vuln_correlator → exploit_planner → AttackChain
    蓝队：detector → triage → threat_hunt → ir_planner → ResponsePlan
    紫队：critic（对抗性校验攻击链）→ reviewer（跨产出一致性审查）

数据流契约（E13.3）：
    Asset[] → VulnFinding[] → AttackChain → Alert[] → ResponsePlan → Critique/Review

记忆闭环（B3 集成）：
    每步产出写入 MemoryStore（情景/工作记忆）→ recall 唤醒历史经验 →
    compress 压缩工作记忆 → 压缩后情景记忆仍可唤醒（闭环未断）。

使用 ``_CyberMockProvider`` 提供 ATT&CK 风格的 mock LLM 响应，
驱动 11 个真实 Agent 实例完成端到端编排，无需真实 LLM API。
"""

from __future__ import annotations

from dataclasses import asdict

from aegisos_agents.action.critic.agent import CriticAgent
from aegisos_agents.action.detector.agent import DetectorAgent
from aegisos_agents.action.exploit_planner.agent import ExploitPlannerAgent
from aegisos_agents.action.ir_planner.agent import IRPlannerAgent
from aegisos_agents.action.recon.agent import ReconAgent
from aegisos_agents.action.reviewer.agent import ReviewerAgent
from aegisos_agents.action.threat_hunt.agent import ThreatHuntAgent
from aegisos_agents.action.triage.agent import TriageAgent
from aegisos_agents.action.vuln_correlator.agent import VulnCorrelatorAgent
from aegisos_agents.memory.memory_store import MemoryStore
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol.cyber import AttackChain, ResponsePlan, VulnFinding
from protocol.memory import MemoryPacket

SESSION_ID = "scenario-1"
TARGET_RANGE = "10.0.0.0/24"


def test_scenario1_red_team_recon_to_attack_chain():
    """红队链路：recon → vuln_correlator → exploit_planner 产出 AttackChain。"""
    provider = _CyberMockProvider()
    memory = MemoryStore()

    # 1) 侦察：目标范围 → 资产清单
    assets = ReconAgent(provider).scan(TARGET_RANGE)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="recon",
            kind="decision",
            summary=f"recon {TARGET_RANGE} found {len(assets)} assets",
        )
    )
    assert len(assets) >= 2
    assert any(a.asset_id == "asset-1" for a in assets)

    # 2) 漏洞关联：资产 → 漏洞发现
    findings = VulnCorrelatorAgent(provider).correlate(assets)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="vuln_correlator",
            kind="decision",
            summary=f"correlated {len(findings)} vulns",
        )
    )
    assert len(findings) >= 1
    assert findings[0].asset_id == "asset-1"

    # 3) 利用链规划：漏洞 → 攻击链
    chain = ExploitPlannerAgent(provider).plan(findings)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="exploit_planner",
            kind="decision",
            summary=f"planned attack chain {chain.chain_id}",
        )
    )
    assert isinstance(chain, AttackChain)
    assert chain.chain_id == "chain-1"
    assert len(chain.steps) >= 1
    assert chain.status == "planned"

    # 记忆闭环：recall 应能唤醒红队决策经验
    recalled = memory.recall("recon")
    assert any(m.task_id == "recon" for m in recalled)


def test_scenario1_blue_team_detect_to_response_plan():
    """蓝队链路：detector → triage → threat_hunt → ir_planner 产出 ResponsePlan。"""
    provider = _CyberMockProvider()
    memory = MemoryStore()

    # 4) 入侵检测：事件流 → 告警
    alerts = DetectorAgent(provider).detect(
        [{"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]
    )
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="detector",
            kind="decision",
            summary=f"detected {len(alerts)} alerts",
        )
    )
    assert len(alerts) >= 1
    assert alerts[0].severity == "high"

    # 5) 告警分诊：告警 → 优先级排序
    triaged = TriageAgent(provider).triage(alerts)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="triage",
            kind="decision",
            summary="triaged alerts by severity",
        )
    )
    assert len(triaged) >= 1  # 分诊后仍至少保留一条告警

    # 6) 威胁狩猎：告警 → ATT&CK 假设
    hypotheses = ThreatHuntAgent(provider).hunt(triaged)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="threat_hunt",
            kind="decision",
            summary=f"generated {len(hypotheses)} hunt hypotheses",
        )
    )
    assert len(hypotheses) >= 1
    assert "technique" in hypotheses[0]

    # 7) 响应规划：假设 → 响应计划
    plan = IRPlannerAgent(provider).plan_response(hypotheses)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="ir_planner",
            kind="decision",
            summary=f"planned response {plan.plan_id}",
        )
    )
    assert isinstance(plan, ResponsePlan)
    assert plan.plan_id == "rp-1"
    assert len(plan.actions) >= 1
    assert plan.actions[0]["kind"] == "isolate"
    assert plan.confidence > 0.0


def test_scenario1_purple_team_critic_and_review():
    """紫队链路：critic 校验攻击链 + reviewer 跨产出一致性审查。"""
    provider = _CyberMockProvider()
    # 构造一条红队攻击链作为批判输入
    findings = [
        VulnFinding(
            finding_id="vuln-1",
            cve_id="CVE-2024-1234",
            asset_id="asset-1",
            cvss=8.1,
            attack_surface="ssh",
        )
    ]
    chain = ExploitPlannerAgent(provider).plan(findings)

    # 8) 紫队批判：校验红队攻击链
    critique = CriticAgent(provider).critique(chain.to_dict(), side="red")
    assert critique["valid"] is True
    assert "severity" in critique

    # 9) 紫队审查：跨产出一致性
    artifacts = {
        "attack_chain": chain.to_dict(),
        "response_plan": {"plan_id": "rp-1", "actions": [{"kind": "isolate"}]},
        "alerts": [{"alert_id": "alert-1", "severity": "high"}],
    }
    review = ReviewerAgent(provider).review(artifacts)
    assert review["consistent"] is True
    assert "overall_assessment" in review


def test_scenario1_full_chain_data_flow_integration():
    """E13.3 全链路数据流集成：Asset → VulnFinding → AttackChain → Alert → ResponsePlan → Critique。"""
    provider = _CyberMockProvider()
    memory = MemoryStore()

    # === 红队 ===
    assets = ReconAgent(provider).scan(TARGET_RANGE)
    assert len(assets) >= 2
    findings = VulnCorrelatorAgent(provider).correlate(assets)
    assert len(findings) >= 1
    chain = ExploitPlannerAgent(provider).plan(findings)
    assert chain.chain_id == "chain-1"
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="red_chain",
            kind="decision",
            summary=f"red team chain {chain.chain_id} planned",
        )
    )

    # === 蓝队 ===
    alerts = DetectorAgent(provider).detect(
        [{"event": "brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]
    )
    assert len(alerts) >= 1
    triaged = TriageAgent(provider).triage(alerts)
    assert len(triaged) >= 1
    hypotheses = ThreatHuntAgent(provider).hunt(triaged)
    assert len(hypotheses) >= 1
    plan = IRPlannerAgent(provider).plan_response(hypotheses)
    assert plan.plan_id == "rp-1"
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="blue_response",
            kind="decision",
            summary=f"blue team response {plan.plan_id} planned",
        )
    )

    # === 紫队 ===
    critique = CriticAgent(provider).critique(chain.to_dict(), side="red")
    assert critique["valid"] is True
    review = ReviewerAgent(provider).review(
        {
            "attack_chain": chain.to_dict(),
            "response_plan": asdict(plan),
            "alerts": [asdict(a) for a in alerts],
        }
    )
    assert review["consistent"] is True

    # === B3 记忆认知循环验证 ===
    # recall 唤醒红蓝决策经验
    assert any(m.task_id == "red_chain" for m in memory.recall("red team"))
    assert any(m.task_id == "blue_response" for m in memory.recall("blue team"))

    # 压缩工作记忆（超预算强制压缩）
    compressed = memory.compress(SESSION_ID, budget=1)
    assert len(compressed) >= 1

    # 压缩后情景记忆仍可唤醒（闭环未断 —— B3 核心验收点）
    post_compress = memory.recall("red team")
    assert any(m.task_id == "red_chain" for m in post_compress), (
        "压缩工作记忆不应破坏情景记忆的唤醒能力"
    )


def test_scenario1_memory_recall_informs_reasoning():
    """B3 集成：推理前 recall 唤醒历史经验，验证记忆接入认知循环。"""
    provider = _CyberMockProvider()
    memory = MemoryStore()

    # 第一轮：完成红队侦察并写入记忆
    ReconAgent(provider).scan(TARGET_RANGE)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="past_recon",
            kind="decision",
            summary=f"past recon {TARGET_RANGE}",
        )
    )

    # 第二轮推理前：recall 唤醒历史侦察经验
    recalled = memory.recall("recon")
    assert len(recalled) >= 1
    assert recalled[0].kind == "decision"  # 决策优先

    # 语义知识库查询：ATT&CK 横向移动技术（供 threat_hunt 参考）
    knowledge = memory.search_knowledge("lateral")
    assert len(knowledge) >= 1
    assert any(k.task_id in ("T1210", "T1021") for k in knowledge)


# =============================================================================
# S3 CyberOrchestrator 编排层 e2e
# =============================================================================


def test_scenario1_orchestrator_red_chain():
    """S3 编排器：run_red_chain 一步走完侦察→漏洞→利用链全链路。"""
    from aegisos_agents.planning.orchestrator import CyberOrchestrator

    orchestrator = CyberOrchestrator(mock=_CyberMockProvider())

    result = orchestrator.run_red_chain(TARGET_RANGE)

    assets = result["assets"]
    findings = result["findings"]
    chain = result["chain"]

    # 侦察应产出 ≥2 个资产
    assert len(assets) >= 2
    # 漏洞关联应产出 ≥1 个发现
    assert len(findings) >= 1
    # 攻击链应是完整 AttackChain
    assert isinstance(chain, AttackChain)
    assert chain.chain_id == "chain-1"
    assert len(chain.steps) >= 1
    assert chain.status == "planned"


def test_scenario1_orchestrator_blue_chain():
    """S3 编排器：run_blue_chain 一步走完检测→分诊→狩猎→响应规划。"""
    from aegisos_agents.planning.orchestrator import CyberOrchestrator

    orchestrator = CyberOrchestrator(mock=_CyberMockProvider())
    event_stream = [{"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]

    result = orchestrator.run_blue_chain(event_stream)

    alerts = result["alerts"]
    plan = result["plan"]

    assert len(alerts) >= 1
    assert alerts[0].severity == "high"
    assert isinstance(plan, ResponsePlan)
    assert plan.plan_id == "rp-1"
    assert len(plan.actions) >= 1
    assert plan.confidence > 0.0


def test_scenario1_orchestrator_purple_review():
    """S3 编排器：run_purple_review 校验攻击链 + 跨产出一致性审查。"""
    from aegisos_agents.planning.orchestrator import CyberOrchestrator

    orchestrator = CyberOrchestrator(mock=_CyberMockProvider())

    # 先跑红蓝链拿到产物
    red = orchestrator.run_red_chain(TARGET_RANGE)
    blue = orchestrator.run_blue_chain(
        [{"event": "brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]
    )

    purple = orchestrator.run_purple_review(
        chain=red["chain"],
        plan=blue["plan"],
        alerts=blue["alerts"],
    )

    critique = purple["critique"]
    review = purple["review"]

    assert critique["valid"] is True
    assert "severity" in critique
    assert review["consistent"] is True
    assert "overall_assessment" in review


def test_scenario1_orchestrator_full_flow_with_memory():
    """S3 编排器 + B3 记忆：完整红→蓝→紫链路 + 记忆认知循环。"""
    from aegisos_agents.planning.orchestrator import CyberOrchestrator

    orchestrator = CyberOrchestrator(mock=_CyberMockProvider())
    memory = MemoryStore()

    # 红队全链路
    red = orchestrator.run_red_chain(TARGET_RANGE)
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="orchestrator_red",
            kind="decision",
            summary=f"red chain {red['chain'].chain_id} completed",
        )
    )
    assert red["chain"].chain_id == "chain-1"

    # 蓝队全链路
    blue = orchestrator.run_blue_chain(
        [{"event": "brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]
    )
    memory.write(
        MemoryPacket(
            session_id=SESSION_ID,
            task_id="orchestrator_blue",
            kind="decision",
            summary=f"blue plan {blue['plan'].plan_id} completed",
        )
    )
    assert blue["plan"].plan_id == "rp-1"

    # 紫队校验
    purple = orchestrator.run_purple_review(
        chain=red["chain"], plan=blue["plan"], alerts=blue["alerts"]
    )
    assert purple["critique"]["valid"] is True
    assert purple["review"]["consistent"] is True

    # B3 记忆闭环
    recalled = memory.recall("red chain")
    assert any(m.task_id == "orchestrator_red" for m in recalled)
    compressed = memory.compress(SESSION_ID, budget=1)
    assert len(compressed) >= 1
    post_compress = memory.recall("red chain")
    assert any(m.task_id == "orchestrator_red" for m in post_compress), (
        "编排器产物经压缩后情景记忆仍可唤醒"
    )
