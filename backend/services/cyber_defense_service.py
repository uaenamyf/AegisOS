# date: 2026-07-06
# dev: Claude Code (glm-5.2)
"""攻防演练服务层。

本模块提供网络安全攻防演练场景的业务编排能力，包括：
    - 靶场会话管理（启动/查询拓扑）
    - 红队攻击链编排（recon→vuln→exploit→lateral）
    - 蓝队防御链编排（detector→triage→hunt→ir_planner）
    - 紫队对抗校验（critic + reviewer）
    - ATT&CK 威胁情报查询

所有编排委托 :class:`CyberOrchestrator`，服务层仅负责参数校验、
结果封装与记忆持久化。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from aegisos_agents.memory.memory_store import MemoryStore
from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks.cyber_provider import _CyberMockProvider
from data.api import GraphStoreAPI, create_graph_store
from protocol.cyber import Asset, AttackChain, ResponsePlan, ThreatIntel


def _asdict(obj):
    return obj.model_dump() if isinstance(obj, BaseModel) else obj


class CyberDefenseService:
    """攻防演练业务编排服务。

    封装 :class:`CyberOrchestrator` 的红蓝紫三条链，提供面向
    REST 端点的高层 API。每次攻防操作的可写入 :class:`MemoryStore`
    以形成记忆闭环。

    Attributes:
        _orchestrator: 内部持有的编排器实例。
        _memory: 记忆存储，用于攻防决策的情景记忆写入。
        _ranges: 活跃靶场会话字典（range_id → RangeSession）。
        _intel_db: ATT&CK 威胁情报种子数据库。
    """

    def __init__(
        self,
        orchestrator: CyberOrchestrator | None = None,
        memory: MemoryStore | None = None,
        graph_store: GraphStoreAPI | None = None,
    ) -> None:
        """初始化攻防服务。

        Args:
            orchestrator: 编排器实例；None 时创建默认 Mock 模式实例。
            memory: 记忆存储；None 时创建临时 MemoryStore。
            graph_store: 可选网络拓扑图存储后端。
        """
        self._orchestrator = orchestrator or CyberOrchestrator(mock=_CyberMockProvider())
        self._memory = memory or MemoryStore()
        self._graph_store = graph_store or create_graph_store("in_memory")
        self._ranges: dict[str, dict[str, Any]] = {}
        self._intel_db = self._seed_intel_db()
        self._drill_dir = Path(__file__).resolve().parent.parent.parent / "data" / "drills"

    # ---- 靶场管理 ----

    def start_range(self, target_range: str, label: str = "") -> dict[str, Any]:
        """启动靶场会话。

        创建一个靶场会话记录，返回会话 ID 和网络拓扑。

        Args:
            target_range: 目标网络范围（如 ``10.0.0.0/24``）。
            label: 可选的靶场标签。

        Returns:
            含 ``range_id`` / ``target_range`` / ``topology`` 的字典。
        """
        import uuid

        range_id = f"range-{uuid.uuid4().hex[:8]}"
        topology = self._generate_topology(target_range)
        self._persist_topology(target_range, topology)

        session = {
            "range_id": range_id,
            "target_range": target_range,
            "label": label or f"Range {target_range}",
            "status": "active",
            "topology": topology,
        }
        self._ranges[range_id] = session
        return session

    def get_topology(self, range_id: str) -> dict[str, Any]:
        """获取靶场网络拓扑。

        Args:
            range_id: 靶场会话 ID。

        Returns:
            含 ``nodes`` / ``edges`` 的拓扑字典。

        Raises:
            KeyError: 靶场会话不存在。
        """
        if range_id not in self._ranges:
            raise KeyError(f"range {range_id} not found")
        return self._ranges[range_id]["topology"]

    def get_range(self, range_id: str) -> dict[str, Any] | None:
        """获取靶场会话信息。

        Args:
            range_id: 靶场会话 ID。

        Returns:
            靶场会话字典；不存在返回 None。
        """
        return self._ranges.get(range_id)

    # ---- 红队攻击 ----

    def red_attack(self, target_range: str) -> dict[str, Any]:
        """执行红队攻击链。

        委托 :meth:`CyberOrchestrator.run_red_chain`，并将各步产出
        写入记忆以形成认知闭环。

        Args:
            target_range: 目标网络范围。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` 的攻击结果字典。
        """
        result = self._orchestrator.run_red_chain(target_range)

        # 写入情景记忆
        chain = result.get("chain")
        chain_id = chain.chain_id if isinstance(chain, AttackChain) else "unknown"
        from protocol.memory import MemoryPacket

        self._memory.write(
            MemoryPacket(
                session_id="cyber-defense",
                task_id="red_attack",
                kind="decision",
                summary=f"red chain {chain_id} planned for {target_range}",
            )
        )

        return self._serialize_red(result)

    def get_attack_chain(self, range_id: str) -> dict[str, Any] | None:
        """获取指定靶场的攻击链 DAG。

        Args:
            range_id: 靶场会话 ID。

        Returns:
            攻击链字典；靶场不存在返回 None。
        """
        session = self._ranges.get(range_id)
        if session is None:
            return None
        # 如果已有缓存的攻击链，返回之；否则触发新的攻击链
        if "attack_chain" in session:
            return session["attack_chain"]
        chain_result = self.red_attack(session["target_range"])
        session["attack_chain"] = chain_result
        return chain_result

    # ---- 蓝队防御 ----

    def blue_defense(
        self, event_stream: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """执行蓝队防御链。

        委托 :meth:`CyberOrchestrator.run_blue_chain`。

        Args:
            event_stream: 原始事件流；None 时使用默认模拟事件。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的防御结果字典。
        """
        if event_stream is None:
            event_stream = [
                {"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"},
                {"event": "port-scan", "src": "10.0.0.99", "dst": "10.0.0.0/24"},
            ]

        result = self._orchestrator.run_blue_chain(event_stream)

        # 写入记忆
        plan = result.get("plan")
        plan_id = plan.plan_id if isinstance(plan, ResponsePlan) else "unknown"
        from protocol.memory import MemoryPacket

        self._memory.write(
            MemoryPacket(
                session_id="cyber-defense",
                task_id="blue_defense",
                kind="decision",
                summary=f"blue defense plan {plan_id} generated",
            )
        )

        return self._serialize_blue(result)

    def get_defense(self, range_id: str) -> dict[str, Any] | None:
        """获取指定靶场的防御响应。

        Args:
            range_id: 靶场会话 ID。

        Returns:
            防御结果字典；靶场不存在返回 None。
        """
        session = self._ranges.get(range_id)
        if session is None:
            return None
        if "defense" in session:
            return session["defense"]
        defense_result = self.blue_defense()
        session["defense"] = defense_result
        return defense_result

    # ---- 紫队校验 ----

    def purple_review(
        self,
        chain: AttackChain | dict[str, Any],
        plan: ResponsePlan | dict[str, Any],
        alerts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """执行紫队对抗校验。

        Args:
            chain: 红队攻击链（dataclass 或 dict）。
            plan: 蓝队响应计划（dataclass 或 dict）。
            alerts: 告警列表。

        Returns:
            含 ``critique`` / ``review`` 的紫队校验结果字典。
        """
        # 统一转换为 dataclass
        if isinstance(chain, dict):
            chain = AttackChain.from_dict(chain)
        if isinstance(plan, dict):
            plan = ResponsePlan(**plan)

        from protocol.cyber import Alert

        alert_objs = [Alert(**a) if isinstance(a, dict) else a for a in alerts]

        result = self._orchestrator.run_purple_review(chain, plan, alert_objs)
        return result

    # ---- 多轮演练（R1/R2） ----

    def drill(
        self,
        target_range: str,
        max_rounds: int = 5,
        on_round=None,
        summary_factory=None,
    ) -> dict[str, Any]:
        """执行一键多轮攻防演练并持久化演练记录。

        委托 :meth:`CyberOrchestrator.run_drill` 跑完「红→蓝→紫」≤max_rounds
        轮并证据驱动收敛；演练结束后将完整记录（每轮战报 + 收敛码 + 总结）
        写入 ``data/drills/<drill_id>.json``，便于回放与审计。

        Args:
            target_range: 目标网络范围（如 ``10.0.0.0/24``）。
            max_rounds: 最大轮数，默认 5。
            on_round: 可选回调 ``on_round(round_data, round_no)``，供 SSE 实时推送。
            summary_factory: 可选总结定制回调；None 时用编排器默认总结。

        Returns:
            含 ``drill_id`` / ``rounds_executed`` / ``convergence_code`` /
            ``rounds`` / ``summary`` 的演练结果字典，并已落盘。
        """
        result = self._orchestrator.run_drill(
            target_range, max_rounds=max_rounds, on_round=on_round
        )
        drill_id = result["drill_id"]
        record = {
            "drill_id": drill_id,
            "target_range": target_range,
            "max_rounds": max_rounds,
            "rounds_executed": result["rounds_executed"],
            "convergence_code": result["convergence_code"],
            "rounds": result["rounds"],
            "summary": result["summary"],
        }
        self._persist_drill(record)
        return record

    def get_drill(self, drill_id: str) -> dict[str, Any] | None:
        """读取已持久化的演练记录。

        Args:
            drill_id: 演练 ID。

        Returns:
            演练记录字典；不存在返回 None。
        """
        path = self._drill_record_path(drill_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def list_drills(self) -> list[dict[str, Any]]:
        """列出所有持久化演练记录的元信息（不含完整战报）。

        Returns:
            每个元素含 ``drill_id`` / ``target_range`` / ``rounds_executed`` /
            ``convergence_code`` 的列表，按生成时间倒序。
        """
        if not self._drill_dir.exists():
            return []
        meta: list[dict[str, Any]] = []
        for path in sorted(self._drill_dir.glob("drill_*.json"), reverse=True):
            rec = self.get_drill(path.stem)
            if rec is None:
                continue
            meta.append(
                {
                    "drill_id": rec.get("drill_id"),
                    "target_range": rec.get("target_range"),
                    "rounds_executed": rec.get("rounds_executed"),
                    "convergence_code": rec.get("convergence_code"),
                    "created_at": rec.get("created_at"),
                }
            )
        return meta

    def _persist_drill(self, record: dict[str, Any]) -> str:
        """将演练记录以 JSON 落盘到 ``data/drills/``。

        Args:
            record: 演练记录字典（须为 JSON 兼容结构）。

        Returns:
            落盘文件路径字符串。
        """
        self._drill_dir.mkdir(parents=True, exist_ok=True)
        path = self._drill_record_path(record["drill_id"])
        record.setdefault("created_at", datetime.now(UTC).isoformat())
        with path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return str(path)

    def _drill_record_path(self, drill_id: str) -> Path:
        """计算演练记录的落盘路径。

        Args:
            drill_id: 演练 ID。

        Returns:
            ``data/drills/<drill_id>.json`` 的 Path。
        """
        return self._drill_dir / f"{drill_id}.json"

    # ---- 威胁情报 ----

    def get_attack_techniques(
        self, tactic: str | None = None
    ) -> list[dict[str, Any]]:
        """查询 ATT&CK 威胁情报。

        Args:
            tactic: 可选的战术过滤；None 时返回全部。

        Returns:
            威胁情报条目列表（dict 格式）。
        """
        if tactic:
            return [_asdict(t) for t in self._intel_db if t.tactic == tactic]
        return [_asdict(t) for t in self._intel_db]

    # ---- 内部辅助 ----

    def _persist_topology(self, scope: str, topology: dict[str, Any]) -> None:
        """将靶场拓扑投影为协议类型并写入图存储。"""
        if self._graph_store is None:
            return
        assets = [
            Asset(
                asset_id=str(node["id"]),
                host=str(node.get("host", "")),
                os=str(node.get("os", "")),
                services=[str(node["role"])] if node.get("role") else [],
            )
            for node in topology.get("nodes", [])
        ]
        links = [
            (str(edge["src"]), str(edge.get("type", "internal")), str(edge["dst"]))
            for edge in topology.get("edges", [])
        ]
        self._graph_store.save_topology(scope, assets, links)

    @staticmethod
    def _generate_topology(target_range: str) -> dict[str, Any]:
        """生成靶场网络拓扑占位。

        Args:
            target_range: 目标网络范围。

        Returns:
            含 ``nodes`` / ``edges`` 的拓扑字典。
        """
        return {
            "target_range": target_range,
            "nodes": [
                {"id": "asset-1", "host": "10.0.0.1", "os": "Linux", "role": "web-server"},
                {"id": "asset-2", "host": "10.0.0.2", "os": "Linux", "role": "db-server"},
                {"id": "asset-3", "host": "10.0.0.3", "os": "Windows", "role": "workstation"},
            ],
            "edges": [
                {"src": "asset-1", "dst": "asset-2", "type": "internal"},
                {"src": "asset-3", "dst": "asset-1", "type": "internal"},
            ],
        }

    @staticmethod
    def _serialize_red(result: dict[str, Any]) -> dict[str, Any]:
        """将红队结果中的 dataclass 序列化为 dict。"""
        assets = result.get("assets", [])
        findings = result.get("findings", [])
        chain = result.get("chain")
        return {
            "assets": [_asdict(a) if not isinstance(a, dict) else a for a in assets],
            "findings": [_asdict(f) if not isinstance(f, dict) else f for f in findings],
            "chain": chain.to_dict() if isinstance(chain, AttackChain) else chain,
        }

    @staticmethod
    def _serialize_blue(result: dict[str, Any]) -> dict[str, Any]:
        """将蓝队结果中的 dataclass 序列化为 dict。"""

        alerts = result.get("alerts", [])
        triaged = result.get("triaged", [])
        hypotheses = result.get("hypotheses", [])
        plan = result.get("plan")
        return {
            "alerts": [_asdict(a) if not isinstance(a, dict) else a for a in alerts],
            "triaged": [_asdict(a) if not isinstance(a, dict) else a for a in triaged],
            "hypotheses": hypotheses,
            "plan": _asdict(plan) if isinstance(plan, ResponsePlan) else plan,
        }

    @staticmethod
    def _seed_intel_db() -> list[ThreatIntel]:
        """初始化 ATT&CK 威胁情报种子数据库。

        Returns:
            预置的威胁情报条目列表。
        """
        return [
            ThreatIntel(
                technique="Command and Scripting Interpreter",
                tactic="Execution",
                technique_id="T1059",
                sub_technique="T1059.004 Unix Shell",
                detection="Monitor for execution of shell commands via auditd or bash history logging.",
                mitigation="Restrict script execution via AppArmor or SELinux policies.",
                risk_level="high",
                refs=["https://attack.mitre.org/techniques/T1059/"],
            ),
            ThreatIntel(
                technique="Brute Force",
                tactic="Credential Access",
                technique_id="T1110",
                sub_technique="T1110.001 Password Guessing",
                detection="Monitor for high-frequency authentication failures in SIEM.",
                mitigation="Implement account lockout policies and MFA.",
                risk_level="high",
                refs=["https://attack.mitre.org/techniques/T1110/"],
            ),
            ThreatIntel(
                technique="Network Service Scanning",
                tactic="Discovery",
                technique_id="T1046",
                detection="Detect SYN scans and port sweeps via IDS/IPS signatures.",
                mitigation="Deploy network segmentation and rate-limiting on exposed ports.",
                risk_level="medium",
                refs=["https://attack.mitre.org/techniques/T1046/"],
            ),
            ThreatIntel(
                technique="Lateral Movement via Remote Services",
                tactic="Lateral Movement",
                technique_id="T1021",
                sub_technique="T1021.004 Remote Desktop Protocol",
                detection="Monitor anomalous RDP sessions and lateral connections.",
                mitigation="Restrict RDP access via network ACLs and jump boxes.",
                risk_level="critical",
                refs=["https://attack.mitre.org/techniques/T1021/"],
            ),
            ThreatIntel(
                technique="Exfiltration Over C2 Channel",
                tactic="Exfiltration",
                technique_id="T1041",
                detection="Monitor for large outbound data transfers to known C2 infrastructure.",
                mitigation="Deploy DLP solutions and egress filtering.",
                risk_level="critical",
                refs=["https://attack.mitre.org/techniques/T1041/"],
            ),
            ThreatIntel(
                technique="Exploit Public-Facing Application",
                tactic="Initial Access",
                technique_id="T1190",
                detection="Monitor web server logs for exploit attempts and WAF alerts.",
                mitigation="Patch public-facing applications and deploy WAF rules.",
                risk_level="critical",
                refs=["https://attack.mitre.org/techniques/T1190/"],
            ),
            ThreatIntel(
                technique="Create Account",
                tactic="Persistence",
                technique_id="T1136",
                sub_technique="T1136.001 Local Account",
                detection="Monitor for new account creation via auditd or Windows Event Log.",
                mitigation="Restrict account creation privileges and audit changes.",
                risk_level="high",
                refs=["https://attack.mitre.org/techniques/T1136/"],
            ),
            ThreatIntel(
                technique="Data Encrypted for Impact",
                tactic="Impact",
                technique_id="T1486",
                detection="Monitor for mass file encryption activity and ransomware signatures.",
                mitigation="Maintain offline backups and deploy EDR with ransomware protection.",
                risk_level="critical",
                refs=["https://attack.mitre.org/techniques/T1486/"],
            ),
        ]
