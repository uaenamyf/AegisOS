# date: 2026-07-06
# dev: myf
"""SDK 编排器 —— 用 openai-agents SDK 的 Agent + handoffs 实现红蓝紫攻防链。

本模块用 SDK 的 ``Agent.handoffs`` 机制串联攻防 Agent，替代
``backend/mocks/runtime.py`` 中 85 行手写的 ``_cyber_dispatch_map()``。

设计要点：
    - **红队攻击链**：recon → vuln_correlator → exploit_planner → lateral_move
      用 SDK handoff 链式传递，每个 Agent 的输出作为下一个 Agent 的输入。
    - **蓝队防御链**：detector → triage → threat_hunt → ir_planner → forensics
    - **紫队闭环**：critic 校验红队产出 → 失败时回 exploit_planner（神经符号循环）
    - **Mock/真实 API 双模式**：注入 MockSDKModel 或真实 SDK Model，两条路径走同一编排

R4.2 SDK handoffs 架构（声明式链 vs 手动串联）：
    - **手动链**（``run_red_chain``）：逐步 ``_run()`` + ``json.dumps`` 传递，
      保留作为默认执行路径（固定顺序管道的正确架构）
    - **handoff 链**（``run_red_chain_via_handoffs``）：SDK ``Agent.handoffs``
      声明式串联，LLM 通过 ``transfer_to_*`` 工具调用触发移交，
      ``on_handoff`` 回调标记各步完成状态到 :class:`ChainContext`
    - **ChainContext**：跨 handoff 共享上下文，累积各步产出（assets/findings/chain）
    - **SDK handoff 规则**：不提供 ``input_type`` 时，``on_handoff`` 回调只接收
      1 个参数 (context)；提供 ``input_type`` 时接收 2 个参数 (context, input)。
      本实现不使用 ``input_type``（中间产出类型不固定），回调只接收 context。

与现有架构的关系：
    - 本模块是 S3 阶段新增的 SDK 原生编排层，位于 ``aegisos_agents/planning/orchestrator/``
    - ``backend/mocks/runtime.py`` 的 MockRuntime 保留作为兼容层（backend DI 依赖）
    - e2e 测试可逐步切换到本编排器
    - 后续 S4 阶段将 backend composition.py 的 runtime 注入切换到本编排器

收益（对比 MockRuntime dispatch map）：
    - 删除 85 行手写 handler + 类型转换
    - SDK handoffs 自动管理状态传递 + 对话历史
    - 获得 SDK 的 tracing（可视化编排流程）+ 流式输出能力
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from pydantic import BaseModel

# R16（WarfareMaster 共享 state 事实源强约束 · 跨 agent 一致性）：
# 真实 LLM 模式下 exploit_planner 的自由文本输出需要确定性修正，确保写回
# state 的攻击链能被蓝队事件流与紫队检阅端一致消费。以下为离线映射表，
# 均不调用 LLM。
_CVE_TECH_ID_RE = re.compile(r"\b(CVE-\d{4}-\d{4,7})\b", re.IGNORECASE)

# CVE → ATT&CK 技法编号（确定性，威胁情报本地库同源）。键统一为大写 CVE。
ATTACK_TECH_BY_CVE: dict[str, str] = {
    "CVE-2023-23397": "T1187",   # Outlook 日历 → NTLM 哈希窃取（凭据访问）
    "CVE-2021-3156": "T1068",    # sudo 堆溢出提权（利用提权漏洞）
    "CVE-2021-4034": "T1068",    # pkexec 提权
    "CVE-2021-41773": "T1190",   # Apache 路径穿越（利用公网应用漏洞）
    "CVE-2021-42013": "T1190",   # Apache 路径穿越 + RCE 变体
    "CVE-2022-0543": "T1203",    # Redis Lua RCE
    "CVE-2017-0144": "T1210",    # 永恒之蓝（利用远程服务漏洞）
    "CVE-2019-0708": "T1210",    # 蓝屏 RDP
    "CVE-2020-1472": "T1210",    # Zerologon
    "CVE-2021-44228": "T1190",   # Log4Shell 初始访问
    "CVE-2017-7494": "T1210",    # Samba RCE
    "CVE-2014-0160": "T1555",    # Heartbleed → 凭据泄露（凭据访问）
    "CVE-2015-7547": "T1068",    # glibc DNS 提权
    "CVE-2018-15473": "T1110",   # OpenSSH 用户枚举 → 爆破
    "CVE-2021-3449": "T1499",    # OpenSSL 拒绝服务
    "CVE-2018-0171": "T1190",    # Smart Install 远程执行
    "CVE-2022-0778": "T1499",    # OpenSSL 无限循环 DoS（端点拒绝服务）
    "CVE-2021-26855": "T1190",    # Exchange SSRF（初始访问）
    "CVE-2019-0211": "T1068",    # Apache 提权
    "CVE-2016-6210": "T1110",    # OpenSSH 用户枚举 → 爆破
    "CVE-2020-1350": "T1499",    # Windows DNS SIGRed 远程 DoS
    "CVE-2022-21907": "T1190",   # HTTP.sys RCE
    "CVE-2011-3192": "T1499",    # Apache Range DoS
    "CVE-2019-15642": "T1190",   # Cacti RCE
    "CVE-2020-0796": "T1210",    # SMBGhost 远程 RCE
    "CVE-2022-22965": "T1190",   # Spring4Shell RCE
    "CVE-2020-15778": "T1190",   # Mongo Express RCE
    "CVE-2020-1938": "T1210",    # AJP Ghostcat 文件读取/RCE
    "CVE-2023-29491": "T1190",   # Langflow 代码执行
    "CVE-2021-20316": "T1190",   # OpenStack 漏洞利用
    "CVE-2019-15846": "T1190",   # Exim 远程命令执行
    # ---- R18b：补全威胁情报种子库（_seed_intel_db）出现的全部 CVE ----
    # 初始访问类：面向公网的应用/服务漏洞
    "CVE-2008-4246": "T1190",    # IIS SVG 解析器远程执行
    "CVE-2010-1429": "T1190",    # Novell iManager 路径穿越
    "CVE-2017-5638": "T1190",    # Apache Struts Multipart OGNL
    "CVE-2017-1000117": "T1190",  # Jenkins CLI 反序列化 RCE
    "CVE-2017-1000410": "T1190",  # Jenkins CLI 反序列化 RCE
    "CVE-2017-12615": "T1190",    # Tomcat PUT 上传 webshell
    "CVE-2018-7600": "T1190",     # Drupalgeddon2 RCE
    "CVE-2019-10149": "T1190",    # Exim 命令注入（MTA）
    "CVE-2019-11510": "T1190",    # Pulse Secure VPN 任意文件读取
    "CVE-2019-15107": "T1190",    # Webmin 远程执行
    "CVE-2020-3452": "T1190",     # Cisco ASA/Firepower 任意文件读取
    "CVE-2020-3580": "T1190",     # Cisco ASA XSS→命令注入
    "CVE-2021-21972": "T1190",    # vCenter 任意文件上传 RCE
    "CVE-2021-26084": "T1190",    # Confluence OGNL 注入 RCE
    "CVE-2023-35332": "T1190",    # MoveIt Transplant 认证绕过上传
    "CVE-2024-3400": "T1190",     # PAN-OS GlobalProtect 命令注入
    "CVE-2024-3094": "T1190",     # XZ Utils 后门（受影响 SSH 服务）
    # 远程服务漏洞利用类
    "CVE-2017-0143": "T1210",     # SMB 家族（EternalRomance 同族）
    "CVE-2017-0145": "T1210",     # SMB 家族
    "CVE-2017-17215": "T1210",    # Huawei UPnP RCE
    "CVE-2024-38063": "T1210",    # Windows TCP RCE
    "CVE-2024-6387": "T1210",     # OpenSSH regreSSHion RCE
    # 客户端执行 / 凭据与中间人 / 拒绝服务
    "CVE-2021-22986": "T1203",    # curl SMB 协议注入（客户端执行）
    "CVE-2016-2183": "T1557",     # SWEET32（TLS DES 会话信息泄露）
    "CVE-2011-4862": "T1499",     # DoS 类
    "CVE-2023-44487": "T1499",    # HTTP/2 Rapid Reset DoS
    "CVE-2023-50387": "T1499",    # DNSSEC RRSIG DoS
}

# 关键词 → ATT&CK 技法编号（长描述启发式，按顺序匹配首个命中）。
_TECH_BY_KEYWORD: list[tuple[str, str]] = [
    ("brute", "T1110"),                # 凭据爆破
    ("password spray", "T1110"),
    ("ntlm", "T1187"),                 # NTLM 窃取/哈希
    ("hash", "T1550"),                 # 哈希传递
    ("pass-the-hash", "T1550.002"),
    ("privilege escalation", "T1068"), # 提权
    ("exploit", "T1210"),              # 漏洞利用
    ("lateral movement", "T1021"),     # 横向移动
    ("remote service", "T1021"),
    ("phishing", "T1566"),             # 钓鱼
    ("command", "T1059"),              # 命令执行
    ("script", "T1059"),
    ("credential", "T1110"),           # 凭据访问
    ("execution", "T1203"),
]

# AP4: 复用规范层（action/）定义的红蓝紫 Agent 作为链上实例，单一事实来源，
# 使 AP4 的 Ask 人机协同方法在运行时编排链路中直接生效（避免编排器内重复定义）。
from aegisos_agents.action.critic.agent import CriticAgent
from aegisos_agents.action.ir_planner.agent import IRPlannerAgent
from aegisos_agents.action.output_types import (
    DetectorResult,
    ExploitPlannerResult,
    ReconResult,
    ReviewResult,
    TriageResult,
    VulnCorrelatorResult,
)
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.action.threat_hunt.agent import ThreatHuntAgent

# P3.2: 低熵稀疏路由（spec 04 §16 / 11 §7 铁律接入）
from aegisos_agents.planning.engine.router.router import route as _route
from aegisos_agents.planning.engine.scheduler.scheduler import Model, schedule
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import (
    Alert,
    Asset,
    AttackChain,
    AttackStep,
    DefenseAction,
    ResponsePlan,
    VulnFinding,
)
from protocol.graph import Graph, GraphNode, NodeKind
from protocol.memory import MemoryPacket
from protocol.message import Message, NodeRef
from protocol.scheduler import Task

if TYPE_CHECKING:
    from aegisos_agents.memory.memory_store import MemoryStore

# R4.2: SDK handoffs 依赖
try:
    from agents import Agent as SDKAgent
    from agents import RunContextWrapper
    from agents.handoffs import handoff

    _SDK_HANDOFF_AVAILABLE = True
except ImportError:
    _SDK_HANDOFF_AVAILABLE = False

# R4.3: SDK output_guardrail 依赖
try:
    from agents import OutputGuardrailTripwireTriggered
    from agents.guardrail import GuardrailFunctionOutput, output_guardrail

    _SDK_GUARDRAIL_AVAILABLE = True
except ImportError:
    _SDK_GUARDRAIL_AVAILABLE = False

# R4.4: SDK tracing 依赖
try:
    from agents import set_trace_processors, trace

    _SDK_TRACING_AVAILABLE = True
except ImportError:
    _SDK_TRACING_AVAILABLE = False

from observability.inspect.monitor.tracing import (
    CyberAgentHooks,
    CyberTraceData,
    CyberTraceProcessor,
)

# R4.5: SDK FunctionTool 依赖
try:
    import agents  # noqa: F401  # ensure SDK available

    _SDK_FUNCTION_TOOL_AVAILABLE = True
except ImportError:
    _SDK_FUNCTION_TOOL_AVAILABLE = False

# AP3: GoalMode 依赖
from aegisos_agents.perception.reasoning.strategies.goal_mode import (
    GoalMode,
    GoalNode,
)


def _asdict(obj):
    return obj.model_dump() if isinstance(obj, BaseModel) else obj


# ==================================================================
# R10: 演练阶段 placement —— 端边云三层候选池 + 各阶段任务特征
# ==================================================================

# 三层候选模型池（演示版：每层一个候选，不接真实异构节点）
# R10.2：edge 增加 review 能力——收敛后增量评审负载下降，可卸载到边侧中型模型
_DRILL_MODEL_POOL: list[Model] = [
    Model(model_id="device_firewall", tier="device", size="small", capabilities=["recon", "detect"]),
    Model(model_id="edge_gateway", tier="edge", size="medium", capabilities=["recon", "detect", "plan", "review"]),
    Model(model_id="cloud_gpu", tier="cloud", size="large", capabilities=["plan", "review", "critique"]),
]

# 各阶段任务特征（按阶段语义设置延迟预算与隐私级别，驱动 schedule() 选层）
#   red    —— 攻击链实时生成：超低延迟 → device/edge
#   blue   —— 防御响应：低延迟 → edge/device
#   purple —— 评审总结：高算力需求 → cloud
_DRILL_PHASE_FEATURES: dict[str, dict[str, Any]] = {
    "red": {
        "goal": "drill red attack chain",
        "latency_budget": 0.8,  # < DEVICE_THRESHOLD(1.0) → 端侧优先
        "privacy": "standard",
        "capability": "recon",
        "reason": "攻击链实时生成（超低延迟）",
    },
    "blue": {
        "goal": "drill blue defense response",
        "latency_budget": 3.0,  # < EDGE_THRESHOLD(5.0) → 边侧优先
        "privacy": "standard",
        "capability": "detect",
        "reason": "防御响应低延迟",
    },
    "purple": {
        "goal": "drill purple review summary",
        "latency_budget": 10.0,  # ≥ EDGE_THRESHOLD → 算力优先 → 云
        "privacy": "unrestricted",
        "capability": "review",
        "reason": "评审总结高算力需求",
    },
}

# 层级语义（供卸载理由展示）
_DRILL_TIER_SEMANTICS: dict[str, str] = {    "device": "端侧·超低延迟/本地隐私",
    "edge": "边侧·低延迟/区域隔离",
    "cloud": "云侧·强算力/可脱敏",
}


class DrillAborted(Exception):
    """演练被用户显式中止（abort）时抛出，用于在 agent 调用边界快速退出。

    由 :meth:`run_drill` 捕获并转为 ``convergence_code="aborted"`` 的收敛结果。
    """

# ==================================================================
# R4.2: ChainContext —— handoff 链共享上下文
# ==================================================================


@dataclass
class ChainContext:
    """Handoff 链共享上下文，累积各步产出。

    在 SDK handoff 链中，每个 ``on_handoff`` 回调将前一个 Agent 的
    结构化产出（JSON dict）写入对应字段。链完成后，由
    :meth:`CyberOrchestrator._context_to_red_result` /
    :meth:`CyberOrchestrator._context_to_blue_result` 转换为 protocol dataclass。

    Attributes:
        target_range: 红队目标范围。
        event_stream: 蓝队原始事件流。
        recon_output: 侦察 Agent 产出（dict）。
        vuln_output: 漏洞关联 Agent 产出（dict）。
        exploit_output: 利用链规划 Agent 产出（dict）。
        detector_output: 入侵检测 Agent 产出（dict）。
        triage_output: 告警分诊 Agent 产出（dict）。
        hunt_output: 威胁狩猎 Agent 产出（dict）。
        ir_output: 响应规划 Agent 产出（dict）。
    """

    target_range: str | None = None
    event_stream: list[dict[str, Any]] = field(default_factory=list)
    # 红队链产出
    recon_output: dict[str, Any] | None = None
    vuln_output: dict[str, Any] | None = None
    exploit_output: dict[str, Any] | None = None
    # 蓝队链产出
    detector_output: dict[str, Any] | None = None
    triage_output: dict[str, Any] | None = None
    hunt_output: dict[str, Any] | None = None
    ir_output: dict[str, Any] | None = None
    # 最终产出
    chain: Any | None = None
    plan: Any | None = None


# ---- 红队 Agent（SDK Agent 定义，供编排用）----


class ReconSDKAgent(StructuredAgent[ReconResult]):
    """红队侦察 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a network reconnaissance agent. Given a target range, "
        "return a JSON object with an 'assets' array. Each asset has "
        "asset_id, host, services (list), os, exposure."
    )
    OUTPUT_TYPE = ReconResult
    TEMPERATURE = 0.3


class VulnCorrelatorSDKAgent(StructuredAgent[VulnCorrelatorResult]):
    """红队漏洞关联 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a vulnerability correlation agent. Given a list of assets, "
        "return JSON with a 'findings' array. Each finding has: finding_id, "
        "cve_id, asset_id, cvss (float), attack_surface."
    )
    OUTPUT_TYPE = VulnCorrelatorResult
    TEMPERATURE = 0.2


class ExploitPlannerSDKAgent(StructuredAgent[ExploitPlannerResult]):
    """红队利用链规划 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an exploit chain planner. Given vulnerability findings, "
        "return JSON with chain_id, target, steps (array of {step_id, technique, "
        "from_asset, to_asset, success}), status."
    )
    OUTPUT_TYPE = ExploitPlannerResult
    TEMPERATURE = 0.4


# ---- 蓝队 Agent ----


class DetectorSDKAgent(StructuredAgent[DetectorResult]):
    """蓝队入侵检测 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an intrusion detection agent. Given an event stream, "
        "return JSON with an 'alerts' array. Each alert has: alert_id, "
        "severity (low|medium|high|critical), src, dst, technique (ATT&CK id), raw (dict)."
    )
    OUTPUT_TYPE = DetectorResult
    TEMPERATURE = 0.2


class TriageSDKAgent(StructuredAgent[TriageResult]):
    """蓝队告警分诊 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are an alert triage agent. Given alerts, return JSON with an "
        "'alerts' array containing deduplicated, severity-ordered alerts."
    )
    OUTPUT_TYPE = TriageResult
    TEMPERATURE = 0.1


class ReviewerSDKAgent(StructuredAgent[ReviewResult]):
    """紫队一致性审查 SDK Agent。"""

    SYSTEM_PROMPT = (
        "You are a consistency reviewer. Given multiple artifacts, check if "
        "they are mutually consistent. Return JSON: consistent (bool), "
        "findings (array), overall_assessment (str)."
    )
    OUTPUT_TYPE = ReviewResult
    TEMPERATURE = 0.2


class CyberOrchestrator(GoalMode[dict]):
    """攻防编排器 —— 用 SDK Agent 实现红蓝紫攻防链。

    封装 11 个 SDK Agent，提供红队攻击链、蓝队防御链、紫队校验的
    编排接口。Mock 模式下注入 :class:`MockSDKModel`，真实 API 模式
    注入 SDK ``OpenAIChatCompletionsModel``。

    AP3：继承 :class:`GoalMode`，支持 :meth:`run_red_chain_with_goal` /
    :meth:`run_blue_chain_with_goal` 递归目标分解编排，替代固定模板链。

    Attributes:
        _mock: Mock Provider 实例（Mock 模式）；真实模式为 None。
        _trace_processor: R4.4 tracing 处理器（enable_tracing 后非 None）。
        _hooks: R4.4 AgentHooks 列表（install_hooks 后非空）。
    """

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4 编排器接入 Ask——新增 ask_handler/eventbus 参数，蓝队 threat_hunt/ir_planner 与紫队 critic 改用规范层 Agent 以复用人机协同能力
    def __init__(
        self,
        mock: MockProvider | None = None,
        model=None,
        ask_handler=None,
        eventbus=None,
    ) -> None:
        """初始化编排器，装配 11 个 SDK Agent。

        Args:
            mock: :class:`MockProvider` 实例（Mock 模式）；真实模式传 None。
            model: SDK ``Model`` 实例（真实 API 模式）；非 None 时优先于 mock，
                由 :meth:`SDKProvider.get_sdk_model` 创建。9 个 Agent 共享同一 Model。
            ask_handler: 可选 :class:`AskHandler`（AP4 人机协同）；下发至
                threat_hunt / ir_planner / critic。None 时各 Agent 退化为
                :class:`AutoAskHandler`（无人值守即时安全降级）。
            eventbus: 可选事件总线；下发至上述三个 Agent，使其发布
                ``HumanInputRequired`` / ``HumanResponse`` 事件供前端渲染。
        """
        self._mock = mock
        # AP4: 保存人机协同 handler，供 _with_human_check 编排方法下发
        self._ask_handler = ask_handler
        # R4.4: tracing 状态
        self._trace_processor: CyberTraceProcessor | None = None
        self._hooks: list[CyberAgentHooks] = []
        # 红队
        self.recon = ReconSDKAgent(mock=mock, model=model)
        self.vuln_correlator = VulnCorrelatorSDKAgent(mock=mock, model=model)
        self.exploit_planner = ExploitPlannerSDKAgent(mock=mock, model=model)
        # 蓝队
        self.detector = DetectorSDKAgent(mock=mock, model=model)
        self.triage = TriageSDKAgent(mock=mock, model=model)
        # AP4: 规范层 Agent（自带 Ask 人机协同能力），注入 ask_handler/eventbus
        self.threat_hunt = ThreatHuntAgent(
            mock=mock, model=model, ask_handler=ask_handler
        )
        self.ir_planner = IRPlannerAgent(
            mock=mock, model=model, ask_handler=ask_handler
        )
        # 紫队
        self.critic = CriticAgent(mock=mock, model=model, ask_handler=ask_handler)
        self.reviewer = ReviewerSDKAgent(mock=mock, model=model)
        # AP4: 将事件总线下发至三个 HITL Agent，使其发布人机协同事件
        if eventbus is not None:
            self.threat_hunt.set_event_bus(eventbus)
            self.ir_planner.set_event_bus(eventbus)
            self.critic.set_event_bus(eventbus)
        # P3.2: 构建低熵路由拓扑（11 个攻防 Agent × 能力映射），供 select_targets 使用
        self._topology: Graph = self._build_topology()

    # P3.2 ----------------------------------------------------------------
    # 低熵稀疏路由：把编排器持有的所有攻防 Agent 映射到 Graph 节点，
    # 通过 RouterAPI.select_targets 提供 Top-K 选取，替代任何"遍历后 dispatch"。

    # date: 2026-08-25
    # dev: myf
    # changelog: P3.2 把 11 个攻防 Agent 映射为 GraphNode（capability=各自 agent_name），
    # 供 select_targets() 走 spec 04 §16 Top-K 稀疏路由
    def _build_topology(self) -> Graph:
        """构建编排器内 Agent 的低熵路由拓扑。

        每个 Agent 作为一个 ``GraphNode`` 注入到 ``Graph``，
        能力标签使用其 agent_name（与 executor 中 ``node.agent_name`` 对齐）。
        Mock 模式下 success_rate=0.5、latency=0.0，真实模式可由运行时心跳注入。
        """
        g = Graph()
        agent_specs: list[tuple[str, str, str]] = [
            # (node_id, kind, capability)
            ("recon", "red", "recon"),
            ("vuln_correlator", "red", "vuln_correlator"),
            ("exploit_planner", "red", "exploit_planner"),
            ("lateral_move", "red", "lateral_move"),
            ("detector", "blue", "detector"),
            ("triage", "blue", "triage"),
            ("threat_hunt", "blue", "threat_hunt"),
            ("ir_planner", "blue", "ir_planner"),
            ("forensics", "blue", "forensics"),
            ("critic", "purple", "critic"),
            ("reviewer", "purple", "reviewer"),
        ]
        for node_id, _side, cap in agent_specs:
            g.add_node(
                GraphNode(
                    node_id=node_id,
                    kind=NodeKind.Agent,
                    capabilities=[cap],
                    success_rate=0.5,
                    latency=0.0,
                    status="active",
                )
            )
        # side 信息保留在 _topology 上（按 node_id 索引）供调试用
        g._side_map = {nid: side for nid, side, _ in agent_specs}  # type: ignore[attr-defined]
        return g

    # date: 2026-08-25
    # dev: myf
    # changelog: P3.2 实现 RouterAPI：按 capability 取 Top-K 目标（spec 04 §16），
    # 内部委派 aegisos_agents.planning.engine.router.route，绝不遍历全图后 dispatch
    def select_targets(
        self, message: Message, required_capability: str
    ) -> list[NodeRef]:
        """按能力选取 Top-K 目标节点（实现 ``RouterAPI``）。"""
        return _route(message, self._topology, required_capability)

    # date: 2026-08-25
    # dev: myf
    # changelog: P3.2 暴露拓扑给调试与编排注入（RouterAPI.get_topology）
    def get_topology(self) -> Graph:
        """返回当前活动 Agent 拓扑（实现 ``RouterAPI``）。"""
        return self._topology

    # date: 2026-08-25
    # dev: myf
    # changelog: P3.2 防御性检查：executor 调用前用稀疏路由确认目标 Agent 在 Top-K 内；
    # 不在则 raise，让 GoalMode 重试或上层处理
    def assert_target_routable(
        self, capability: str, target_agent_name: str
    ) -> None:
        """稀疏路由前置守卫：要求目标 Agent 在当前能力 Top-K 候选里。

        Args:
            capability: 能力标识（如 ``"recon"``）。
            target_agent_name: 编排器即将调用的 Agent 名称（与 node.agent_name 对齐）。

        Raises:
            ValueError: 当目标不在 ``select_targets(...)`` 返回的 Top-K 中时抛出，
                用于阻断任何"绕过路由直接调用"的违规路径。
        """
        targets = _route(Message(), self._topology, capability)
        if not any(t.node_id == target_agent_name for t in targets):
            raise ValueError(
                f"Agent {target_agent_name!r} not in Top-K for capability "
                f"{capability!r} (candidates={[t.node_id for t in targets]})"
            )
    # ---------------------------------------------------------------------

    def run_red_chain(
        self,
        target_range: str,
        round: int | None = None,
        abort: Callable[[], bool] | None = None,
        critique_feedback: str | None = None,
    ) -> dict[str, Any]:
        """执行红队攻击链：recon → vuln_correlator → exploit_planner。

        R1/R1.5：新增可选 ``round`` 参数用于多轮收敛演练——显式传入且 >=2 时
        在 recon/exploit 的 prompt 注入 ``[round=N]`` 标记，触发 mock 按轮演化
        （第 N 轮才暴露新资产/新利用步骤），驱动多轮对抗收敛真实可演示。
        默认 round=None 完全保持旧行为，既有调用/测试零破坏。

        R16（WarfareMaster 共享 state 事实源强约束）：新增可选
        ``critique_feedback`` —— 由 run_drill 传入上一轮紫队 critique 的
        issues 摘要，注入 exploit prompt 让红队按评审要求修正（消除
        self-loop/技法重复/目标不一致等），实现"紫队反馈驱动红队演化"闭环；
        同时 exploit 输出经资产命名归一化 + ATT&CK 技法编号兜底后写回 state，
        保证蓝队事件流与紫队检阅端一致消费。

        R14：返回字典附加 ``agent_trace``——每个 agent 的输入 prompt 与结构化
        输出（用于 Auto Drill 运行记录报告，排查每个 agent 的输入输出）。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。
            round: 显式演练轮次（>=2 触发演化）；None 表示不演化。
            abort: 可选中止回调。
            critique_feedback: 上一轮紫队 critique 的 issues 摘要（None 不注入）。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` / ``agent_trace`` 的字典
            （值为 protocol dataclass）。
        """
        round_tag = f" [round={round}]" if round is not None and round >= 2 else ""
        fb_tag = (
            f"\n[上一轮紫队评审意见——请修正缺陷,但保留完整的攻击链路径]\n"
            f"不要删减步骤或只保留初始访问;根据意见修正技法编号/消除自环/补齐横向移动与提权,"
            f"输出一条从外部到最终目标 agent 资产的完整多步链。\n{critique_feedback}"
            if critique_feedback
            else ""
        )
        trace: list[dict[str, Any]] = []
        if abort is not None and abort():
            raise DrillAborted()
        # 1) 侦察（数量上限截断：提速——限制 DeepSeek 输出规模，下同）
        recon_prompt = f"Scan target range: {target_range}{round_tag}"
        recon_result = self.recon._run(recon_prompt)
        trace.append(self._trace_entry("recon", recon_prompt, recon_result))
        if abort is not None and abort():
            raise DrillAborted()
        # R16（WarfareMaster 共享 state 单一事实源）：recon 是自由文本 LLM 输出，
        # asset_id 在真实模式下不可靠（R2 直接拿 IP 当 ID、R3 幻觉 asset-006）。
        # 因此由编排器统一分配稳定资产 ID（asset-001…按 host 去重排序），
        # recon 的 asset_id 仅作参考、一律以编排器分配为准；host 才是资产事实锚点。
        recon_raw = recon_result.assets[:8]
        _host_order: list[str] = []
        for a in recon_raw:
            h = (a.host or "").strip()
            if h and h not in _host_order:
                _host_order.append(h)
        _host_to_id = {h: f"asset-{i + 1:03d}" for i, h in enumerate(_host_order)}
        _id_to_host = {v: k for k, v in _host_to_id.items()}
        assets = [
            Asset(
                # 用编排器分配的稳定 ID 覆盖 LLM 自由生成的 asset_id（host 才是事实）
                asset_id=_host_to_id[h],
                host=h,
                services=a.services,
                os=a.os,
                exposure=a.exposure,
            )
            for a, h in ((a, (a.host or "").strip()) for a in recon_raw)
            if h in _host_to_id
        ]

        # 2) 漏洞关联
        assets_desc = json.dumps(
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        vuln_prompt = f"Correlate vulnerabilities for these assets: {assets_desc}"
        vuln_result = self.vuln_correlator._run(vuln_prompt)
        trace.append(self._trace_entry("vuln_correlator", vuln_prompt, vuln_result))
        if abort is not None and abort():
            raise DrillAborted()
        findings = [
            VulnFinding(
                finding_id=f.finding_id,
                cve_id=f.cve_id,
                # asset_id 可能也是自由文本（IP/幻觉 ID），统一归一化到编排器分配的稳定 ID
                asset_id=self._resolve_asset_id(f.asset_id, _host_to_id, _id_to_host),
                cvss=f.cvss,
                attack_surface=f.attack_surface,
            )
            for f in vuln_result.findings[:8]
        ]

        # 3) 利用链规划
        findings_desc = json.dumps(
            [
                {
                    "finding_id": f.finding_id,
                    "cve_id": f.cve_id,
                    "asset_id": f.asset_id,
                    "cvss": f.cvss,
                }
                for f in findings
            ]
        )
        exploit_prompt = f"Plan exploit chain for: {findings_desc}{round_tag}{fb_tag}"
        exploit_result = self.exploit_planner._run(exploit_prompt)
        trace.append(self._trace_entry("exploit_planner", exploit_prompt, exploit_result))
        if abort is not None and abort():
            raise DrillAborted()
        chain = AttackChain(
            chain_id=exploit_result.chain_id,
            target=exploit_result.target,
            steps=[AttackStep(**s.model_dump()) for s in exploit_result.steps[:6]],
            status=exploit_result.status,
        )

        # WarfareMaster 共享 state 事实源强约束（跨 agent 一致性，R16）：
        # exploit_planner 是自由文本 LLM 输出，from/to_asset 可能产出 host IP 而非
        # asset_id、technique 可能是长描述而非 ATT&CK 编号 —— 若直接写入 state，
        # _synthesize_event_stream 合成的蓝队事件流与紫队检阅的链路就会与
        # recon 资产对上 / 对不上（reviewer 判 inconsistent 的真凶）。
        # 因此在写回 state 前做两个确定性修正：
        #   1) 资产命名归一：host → canonical asset_id；匹配不到的孤立步骤丢弃。
        #   2) ATT&CK 技法编号补齐：长描述/CVE → 确定性 T1xxx（离线映射，不调 LLM）。
        assets_by_host = {a.host.lower(): a.asset_id for a in assets}
        assets_by_id = {a.asset_id: a.asset_id for a in assets}
        # 兼容命名差异（real LLM 偶发 asset-2 vs asset-002 / asset_1）：数字指纹模糊匹配
        def _id_match(token: str) -> str | None:
            direct = _id_to_host.get(token)
            if direct:
                return token
            m = re.search(r"(\d+)", token)
            if m:
                want = m.group(1).lstrip("0")
                for aid in _id_to_host:
                    am = re.search(r"(\d+)", aid)
                    if am and am.group(1).lstrip("0") == want:
                        return aid
            return None
        # 外部攻击起点（非资产）合法标识：from_asset 匹配不到资产时归一化为统一标记
        _EXTERNAL_TOKENS = {"attacker", "attacker-controlled", "external", "internet", "public"}
        normal_steps: list[AttackStep] = []
        used_cves: set[str] = set()
        for s in chain.steps:
            src = (s.from_asset or "").strip()
            dst = (s.to_asset or "").strip()
            src_norm = assets_by_host.get(src.lower()) or _id_match(src)
            dst_norm = assets_by_host.get(dst.lower()) or _id_match(dst)
            # 目标资产必须可解析 —— 否则该步骤无法进入蓝队事件流，丢弃
            if not dst_norm:
                continue
            # 起点：匹配不到资产时，若是外部攻击者标识则归一化为 "external"，否则丢弃
            if not src_norm:
                if src.lower() not in _EXTERNAL_TOKENS:
                    continue
                src_norm = "external"
            s.from_asset = src_norm
            s.to_asset = dst_norm
            s.technique = self._ensure_technique_id(s.technique)
            # R18：技法纯编号时补 CVE 证据（紫队要求每步有漏洞/凭据论证），
            # 全链 CVE 不复用（used_cves 记账）
            s.technique = self._step_evidence(findings, s, used_cves)
            normal_steps.append(s)
        chain.steps = normal_steps
        # R18：字段自洽确定性修正——全部步骤 success=true 但 status 仍 planned 时，
        # 改为 completed（紫队挑"全成功却计划中"矛盾；prompt 第 3 条的硬保险）
        if chain.steps and all(s.success for s in chain.steps) and chain.status == "planned":
            chain.status = "completed"

        return {"assets": assets, "findings": findings, "chain": chain, "agent_trace": trace}

    @staticmethod
    def _resolve_asset_id(
        raw: str,
        host_to_id: dict[str, str],
        id_to_host: dict[str, str],
    ) -> str:
        """把自由文本资产引用归一化到编排器分配的稳定 asset_id。

        - 已是稳定 ID（asset-001…）→ 原样返回。
        - 是 host/IP（10.0.0.1…）→ 查 host_to_id 映射。
        - 数字指纹模糊匹配（asset-2 / asset_2 → asset-002）。
        - 均不匹配 → 返回原始值（由后续步骤级归一化丢弃孤立步骤）。
        """
        tok = (raw or "").strip()
        if not tok:
            return ""
        if tok in id_to_host:
            return tok
        low = tok.lower()
        if low in host_to_id:
            return host_to_id[low]
        m = re.search(r"(\d+)", tok)
        if m:
            want = m.group(1).lstrip("0")
            for aid in id_to_host:
                am = re.search(r"(\d+)", aid)
                if am and am.group(1).lstrip("0") == want:
                    return aid
        return tok

    @staticmethod
    def _ensure_technique_id(technique: str) -> str:
        """ATT&CK 技法编号兜底：真实 LLM 输出长描述/仅 CVE 时，映射到确定性 T 编号。

        - 已是 ``T\\d+(?:.\\d+)?`` 形式 → 原样返回。
        - 长描述里含 CVE 编号 → 查 CVE→T 映射表。
        - 其余 → 按关键漏洞/攻击面关键词启发式映射（ATT&CK Enterprise 语义）。
        """
        t = technique.strip()
        # 已是纯 T 编号 → 原样返回
        if re.match(r"^T\d+(?:\.\d+)?$", t):
            return t
        # 以 T 编号开头但带证据后缀（如 "T1190 (CVE-2021-26855) — Exchange SSRF"）：
        # 保留开头编号+证据整体，紫队既能取编号也能看到 CVE 论证（R18）
        if re.match(r"^(T\d+(?:\.\d+)?)\b", t):
            return t
        cve = _CVE_TECH_ID_RE.search(t)
        if cve:
            key = cve.group(1).upper()
            mapped = ATTACK_TECH_BY_CVE.get(key)
            if mapped:
                return mapped
        # 关键词启发式（黑名单/凭据/漏洞利用/横向移动等）
        low = t.lower()
        for pattern, tech in _TECH_BY_KEYWORD:
            if pattern in low:
                return tech
        # 兜底：保留原文，但至少确保首字母规范（不会因缺编号被判无效）
        return t

    @staticmethod
    def _step_evidence(
        findings: list[VulnFinding], step: AttackStep, used_cves: set[str]
    ) -> str:
        """把 technique 字段规范化为 "<Txxxxx> (<CVE> on <资产>)" 落地格式。

        R18b：deepseek 频繁违反 prompt 契约——只给纯编号（缺证据）、幻觉
        findings 之外的 CVE、CVE 与编号语义不匹配，都会招紫队批评。这里做
        确定性规范化：
        - 证据 CVE 只认 findings 里的真实漏洞，且全链不复用（used_cves 记账）；
        - CVE→技法映射存在时以 CVE 反推编号（保证 "编号 vs CVE" 语义一致，
          紫队不再挑矛盾）；模型自述编号次之，关键词启发再次，T1210 通用兜底；
        - 模型自带证据但 CVE 是幻觉的 → 换成落地 CVE。
        """
        tech = (step.technique or "").strip()
        to_a = (step.to_asset or "").strip()
        cve_set = {
            (f.cve_id or "").strip().upper() for f in findings if (f.cve_id or "").strip()
        }
        # 模型自述的开头 T 编号（若有）
        t_own = re.match(r"^(T\d+(?:\.\d+)?)\b", tech)
        # 模型自述的、且在 findings 中落地、且未被前面步骤占用的 CVE
        cve = next(
            (
                c.upper()
                for c in re.findall(r"CVE-\d{4}-\d{4,7}", tech, re.IGNORECASE)
                if c.upper() in cve_set and c.upper() not in used_cves
            ),
            "",
        )
        if not cve:
            tl = to_a.lower()
            cve = next(
                (
                    f.cve_id.upper()
                    for f in findings
                    if (f.cve_id or "").strip()
                    and (f.asset_id or "").strip().lower() == tl
                    and f.cve_id.upper() not in used_cves
                ),
                "",
            ) or next(
                (
                    f.cve_id.upper()
                    for f in findings
                    if (f.cve_id or "").strip() and f.cve_id.upper() not in used_cves
                ),
                "",
            )
        if cve:
            used_cves.add(cve)
        # 编号：CVE 反推优先（语义一致硬保证）→ 模型自述编号 → 关键词 → 通用
        mapped = ATTACK_TECH_BY_CVE.get(cve) if cve else None
        tc = mapped or (t_own.group(1) if t_own else "")
        if not tc:
            for pattern, tech_id in _TECH_BY_KEYWORD:
                if pattern in tech.lower():
                    tc = tech_id
                    break
        if not tc and cve:
            tc = "T1210"
        if tc and cve:
            return f"{tc} ({cve} on {to_a})" if to_a else f"{tc} ({cve})"
        if tc:
            return tc
        return tech

    @staticmethod
    def _trace_entry(agent: str, prompt: str, result: Any) -> dict[str, Any]:
        """构造 agent 级调用追踪条目（输入 prompt + 结构化输出）。

        Args:
            agent: agent 标识（如 ``recon`` / ``detector`` / ``ir_planner``）。
            prompt: 实际发送给 LLM/mock 的输入文本。
            result: agent 的 ``_run`` 返回结果（pydantic 模型或 dataclass）。

        Returns:
            ``{"agent", "input", "output"}`` 字典，输出为 JSON 兼容结构。
        """
        if hasattr(result, "model_dump"):
            output = result.model_dump()
        elif hasattr(result, "to_dict"):
            output = result.to_dict()
        else:
            output = _asdict(result)
        return {"agent": agent, "input": prompt, "output": output}

    async def stream_red_chain(self, target_range: str, round: int | None = None):
        """红队链流式执行（供 SSE 渐进展示）。

        与 :meth:`run_red_chain` 相同的三步链，但逐步 ``yield`` 阶段事件：
            - ``{"event": "stage_start", "data": {"stage": ...}}``
            - ``{"event": "stage_done", "data": {...}}``（各步产出）
            - ``{"event": "done", "data": {"assets", "findings", "chain"}}``
        每步同步 LLM 调用投递到线程池（``asyncio.to_thread``）避免阻塞
        事件循环；与真实模式 StructuredAgent 的线程池路径天然兼容。
        同样执行 8 资产 / 8 漏洞 / 6 步的数量上限截断（提速器）。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。
            round: 显式演练轮次（>=2 触发演化）；None 表示不演化。

        Yields:
            dict: 阶段事件（stage_start / stage_done / done）。
        """
        round_tag = f" [round={round}]" if round is not None and round >= 2 else ""

        # 1) 侦察
        yield {"event": "stage_start", "data": {"stage": "recon"}}
        recon_result = await asyncio.to_thread(
            self.recon._run, f"Scan target range: {target_range}{round_tag}"
        )
        assets = [
            Asset(
                asset_id=a.asset_id, host=a.host, services=a.services, os=a.os, exposure=a.exposure
            )
            for a in recon_result.assets[:8]
        ]
        yield {"event": "stage_done", "data": {"stage": "recon", "assets": assets}}

        # 2) 漏洞关联
        yield {"event": "stage_start", "data": {"stage": "vuln"}}
        assets_desc = json.dumps(
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        vuln_result = await asyncio.to_thread(
            self.vuln_correlator._run,
            f"Correlate vulnerabilities for these assets: {assets_desc}",
        )
        findings = [
            VulnFinding(
                finding_id=f.finding_id,
                cve_id=f.cve_id,
                asset_id=f.asset_id,
                cvss=f.cvss,
                attack_surface=f.attack_surface,
            )
            for f in vuln_result.findings[:8]
        ]
        yield {"event": "stage_done", "data": {"stage": "vuln", "findings": findings}}

        # 3) 利用链规划
        yield {"event": "stage_start", "data": {"stage": "exploit"}}
        findings_desc = json.dumps(
            [
                {
                    "finding_id": f.finding_id,
                    "cve_id": f.cve_id,
                    "asset_id": f.asset_id,
                    "cvss": f.cvss,
                }
                for f in findings
            ]
        )
        exploit_result = await asyncio.to_thread(
            self.exploit_planner._run,
            f"Plan exploit chain for: {findings_desc}{round_tag}",
        )
        chain = AttackChain(
            chain_id=exploit_result.chain_id,
            target=exploit_result.target,
            steps=[AttackStep(**s.model_dump()) for s in exploit_result.steps[:6]],
            status=exploit_result.status,
        )
        yield {"event": "stage_done", "data": {"stage": "exploit", "chain": chain}}
        yield {"event": "done", "data": {"assets": assets, "findings": findings, "chain": chain}}

    def run_blue_chain(
        self,
        event_stream: list[dict[str, Any]],
        abort: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        """执行蓝队防御链：detector → triage → threat_hunt → ir_planner。

        Args:
            event_stream: 原始事件流列表。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` / ``agent_trace`` 的字典。
        """
        trace: list[dict[str, Any]] = []
        if abort is not None and abort():
            raise DrillAborted()
        # 1) 入侵检测
        detector_prompt = f"Detect anomalies in: {json.dumps(event_stream)}"
        detector_result = self.detector._run(detector_prompt)
        trace.append(self._trace_entry("detector", detector_prompt, detector_result))
        if abort is not None and abort():
            raise DrillAborted()
        alerts = [
            Alert(
                alert_id=a.alert_id,
                severity=a.severity,
                src=a.src,
                dst=a.dst,
                technique=a.technique,
                raw=a.raw,
            )
            for a in detector_result.alerts
        ]

        # 2) 告警分诊
        alerts_desc = json.dumps(
            [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity,
                    "src": a.src,
                    "dst": a.dst,
                    "technique": a.technique,
                }
                for a in alerts
            ]
        )
        triage_prompt = f"Triage these alerts: {alerts_desc}"
        triage_result = self.triage._run(triage_prompt)
        trace.append(self._trace_entry("triage", triage_prompt, triage_result))
        if abort is not None and abort():
            raise DrillAborted()
        triaged = [Alert(**t.model_dump()) for t in triage_result.alerts] or alerts

        # 3) 威胁狩猎
        hunt_prompt = f"Generate hunting hypotheses for: {alerts_desc}"
        hunt_result = self.threat_hunt._run(hunt_prompt)
        trace.append(self._trace_entry("threat_hunt", hunt_prompt, hunt_result))
        if abort is not None and abort():
            raise DrillAborted()
        hypotheses = [h.model_dump() for h in hunt_result.hypotheses]

        # 4) 响应规划
        ir_prompt = f"Plan response for: {json.dumps(hypotheses)}"
        ir_result = self.ir_planner._run(ir_prompt)
        trace.append(self._trace_entry("ir_planner", ir_prompt, ir_result))
        if abort is not None and abort():
            raise DrillAborted()
        plan = ResponsePlan(
            plan_id=ir_result.plan_id,
            actions=[
                DefenseAction.model_validate(a.model_dump())
                for a in ir_result.actions
            ],
            confidence=ir_result.confidence,
            rollback=ir_result.rollback,
        )

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
            "agent_trace": trace,
        }

    async def stream_blue_chain(self, event_stream: list[dict[str, Any]]):
        """蓝队链流式执行（供 SSE 渐进展示）。

        与 :meth:`run_blue_chain` 相同的四步链，但逐步 ``yield`` 阶段事件：
            - ``{"event": "stage_start", "data": {"stage": ...}}``
            - ``{"event": "stage_done", "data": {...}}``（各步产出）
            - ``{"event": "done", "data": {"alerts", "triaged", "hypotheses", "plan", "agent_trace"}}``
        每步同步 LLM 调用投递到线程池（``asyncio.to_thread``）避免阻塞
        事件循环；与真实模式 StructuredAgent 的线程池路径天然兼容。

        Args:
            event_stream: 原始事件流列表。

        Yields:
            dict: 阶段事件（stage_start / stage_done / done）。
        """
        trace: list[dict[str, Any]] = []

        # 1) 入侵检测
        yield {"event": "stage_start", "data": {"stage": "detect"}}
        detector_prompt = f"Detect anomalies in: {json.dumps(event_stream)}"
        detector_result = await asyncio.to_thread(
            self.detector._run, detector_prompt
        )
        trace.append(self._trace_entry("detector", detector_prompt, detector_result))
        alerts = [
            Alert(
                alert_id=a.alert_id,
                severity=a.severity,
                src=a.src,
                dst=a.dst,
                technique=a.technique,
                raw=a.raw,
            )
            for a in detector_result.alerts
        ]
        yield {"event": "stage_done", "data": {"stage": "detect", "alerts": alerts}}

        # 2) 告警分诊
        yield {"event": "stage_start", "data": {"stage": "triage"}}
        alerts_desc = json.dumps(
            [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity,
                    "src": a.src,
                    "dst": a.dst,
                    "technique": a.technique,
                }
                for a in alerts
            ]
        )
        triage_prompt = f"Triage these alerts: {alerts_desc}"
        triage_result = await asyncio.to_thread(self.triage._run, triage_prompt)
        trace.append(self._trace_entry("triage", triage_prompt, triage_result))
        triaged = [Alert(**t.model_dump()) for t in triage_result.alerts] or alerts
        yield {"event": "stage_done", "data": {"stage": "triage", "triaged": triaged}}

        # 3) 威胁狩猎
        yield {"event": "stage_start", "data": {"stage": "hunt"}}
        hunt_prompt = f"Generate hunting hypotheses for: {alerts_desc}"
        hunt_result = await asyncio.to_thread(self.threat_hunt._run, hunt_prompt)
        trace.append(self._trace_entry("threat_hunt", hunt_prompt, hunt_result))
        hypotheses = [h.model_dump() for h in hunt_result.hypotheses]
        yield {"event": "stage_done", "data": {"stage": "hunt", "hypotheses": hypotheses}}

        # 4) 响应规划
        yield {"event": "stage_start", "data": {"stage": "ir"}}
        ir_prompt = f"Plan response for: {json.dumps(hypotheses)}"
        ir_result = await asyncio.to_thread(self.ir_planner._run, ir_prompt)
        trace.append(self._trace_entry("ir_planner", ir_prompt, ir_result))
        plan = ResponsePlan(
            plan_id=ir_result.plan_id,
            actions=[
                DefenseAction.model_validate(a.model_dump())
                for a in ir_result.actions
            ],
            confidence=ir_result.confidence,
            rollback=ir_result.rollback,
        )
        yield {"event": "stage_done", "data": {"stage": "ir", "plan": plan}}
        yield {
            "event": "done",
            "data": {
                "alerts": alerts,
                "triaged": triaged,
                "hypotheses": hypotheses,
                "plan": plan,
                "agent_trace": trace,
            },
        }

    def run_purple_review(
        self,
        chain: AttackChain,
        plan: ResponsePlan,
        alerts: list[Alert],
        round: int | None = None,
        prior_rounds_summary: str | None = None,
        abort: Callable[[], bool] | None = None,
        assets: list[Asset] | None = None,
    ) -> dict[str, Any]:
        """执行紫队校验：critic 校验攻击链 + reviewer 跨产出一致性审查。

        R18b：新增可选 ``assets``——把侦察得到的资产清单（host/os/services/
        exposure）作为共享事实注入 critic 与 reviewer 的 prompt。之前紫队拿不到
        资产属性，只能臆测"asset-001 未标明是否为 Linux"而反复判不合格；现
        以编排器 state 的资产事实为准绳，critic 可据实校验 CVE 与资产类型是否自洽。

        R1/R1.5：新增可选 ``round`` 参数——显式传入时 critic 的 prompt 注入
        ``[round=N]`` 触发 mock 按轮演化（round=1 判缺口 valid=False，>=2 补齐
        valid=True）。默认 round=None 保持旧行为，既有调用/测试零破坏。

        R8：新增可选 ``prior_rounds_summary`` 参数——显式传入时在 critic 与
        reviewer 的 prompt 注入 ``[prior_rounds_summary]`` 片段，使紫队评审携带
        前序轮次决策摘要（跨轮记忆），对抗长链推理的注意力稀释与记忆坍缩。
        默认 None 完全保持旧行为。

        Args:
            chain: 红队攻击链产出。
            plan: 蓝队响应计划产出。
            alerts: 蓝队告警列表。
            round: 显式演练轮次；None 表示不演化（默认）。
            prior_rounds_summary: 前序轮次压缩摘要文本；None 表示不注入（默认）。

        Returns:
            含 ``critique`` / ``review`` / ``agent_trace`` 的字典（均为 dict）。
        """
        trace: list[dict[str, Any]] = []
        # 紫队批判红队攻击链
        if abort is not None and abort():
            raise DrillAborted()
        round_tag = f" [round={round}]" if round is not None else ""
        prior_tag = (
            f"\n[prior_rounds_summary] {prior_rounds_summary}"
            if prior_rounds_summary
            else ""
        )
        critique_prompt = f"Critique: {json.dumps(chain.to_dict())}{round_tag}{prior_tag}{self._assets_tag(assets)}"
        critique_result = self.critic._run(critique_prompt)
        trace.append(self._trace_entry("critic", critique_prompt, critique_result))
        critique = critique_result.model_dump()

        # 紫队跨产出一致性审查
        artifacts = {
            "attack_chain": chain.to_dict(),
            "response_plan": _asdict(plan),
            "alerts": [_asdict(a) for a in alerts],
            "prior_rounds_summary": prior_rounds_summary,
        }
        if assets:
            artifacts["assets_context"] = [
                {
                    "asset_id": a.asset_id,
                    "host": a.host,
                    "os": a.os,
                    "services": a.services,
                    "exposure": a.exposure,
                }
                for a in assets
            ]
        review_prompt = f"Review consistency: {json.dumps(artifacts, default=str)}"
        review_result = self.reviewer._run(review_prompt)
        trace.append(self._trace_entry("reviewer", review_prompt, review_result))
        if abort is not None and abort():
            raise DrillAborted()
        review = review_result.model_dump()

        return {"critique": critique, "review": review, "agent_trace": trace}

    @staticmethod
    def _assets_tag(assets: list[Asset] | None) -> str:
        """资产清单事实源片段（R18b）：供紫队据实校验 CVE×资产类型。"""
        if not assets:
            return ""
        rows = "; ".join(
            f"{a.asset_id}(os={a.os or 'unknown'}, exposure={a.exposure or 'unknown'}, "
            f"services={','.join(a.services) if a.services else 'none'})"
            for a in assets
        )
        return f"\n[assets context — ground truth for OS/exposure checks] {rows}"

    # ==================================================================
    # AP4: 带人机协同（Ask 范式）的攻防编排方法
    # ==================================================================

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4 新增 run_blue_chain_with_human_check——蓝队防御链在威胁狩猎与响应规划处接入人机确认
    def run_blue_chain_with_human_check(
        self,
        event_stream: list[dict[str, Any]],
        ask_handler=None,
        confidence_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """执行带人机协同的蓝队防御链（AP4）。

        链路同 :meth:`run_blue_chain`（detector → triage → threat_hunt →
        ir_planner），但在 threat_hunt 假设置信度偏低、ir_planner 计划含破坏性
        动作时插入人工确认闸门（Ask 范式），超时/无人值守自动保守降级，
        不阻塞整条防御链。

        Args:
            event_stream: 原始事件流列表。
            ask_handler: 可选 :class:`AskHandler`；None 时使用编排器初始化时的 handler。
            confidence_threshold: 触发澄清的置信度下限。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        # 1) 入侵检测（无需人工确认）
        detector_result = self.detector._run(f"Detect anomalies in: {json.dumps(event_stream)}")
        alerts = [
            Alert(
                alert_id=a.alert_id,
                severity=a.severity,
                src=a.src,
                dst=a.dst,
                technique=a.technique,
                raw=a.raw,
            )
            for a in detector_result.alerts
        ]

        # 2) 告警分诊（无需人工确认）
        alerts_desc = json.dumps(
            [
                {"alert_id": a.alert_id, "severity": a.severity, "src": a.src, "dst": a.dst}
                for a in alerts
            ]
        )
        triage_result = self.triage._run(f"Triage these alerts: {alerts_desc}")
        triaged = [Alert(**t.model_dump()) for t in triage_result.alerts] or alerts

        # 3) 威胁狩猎（低置信度假设时暂停澄清）
        hunt_handler = ask_handler or self._ask_handler
        hypotheses = self.threat_hunt.hunt_with_human_check(
            triaged, confidence_threshold=confidence_threshold, ask_handler=hunt_handler
        )

        # 4) 响应规划（破坏性动作前确认）
        ir_handler = ask_handler or self._ask_handler
        plan = self.ir_planner.plan_response_with_human_check(
            hypotheses, ask_handler=ir_handler
        )

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
        }

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4 新增 run_purple_review_with_human_check——紫队批判严重度达阈值时请求人工复核
    def run_purple_review_with_human_check(
        self,
        chain: AttackChain,
        plan: ResponsePlan,
        alerts: list[Alert],
        ask_handler=None,
        severity_threshold: str = "high",
    ) -> dict[str, Any]:
        """执行带人机协同的紫队校验（AP4）。

        同 :meth:`run_purple_review` 的 reviewer 一致性审查，但 critic 批判在
        判定严重度达到 ``severity_threshold`` 时暂停请求人工复核（Ask 范式），
        超时/无人值守降级为确认结论并标记。

        Args:
            chain: 红队攻击链产出。
            plan: 蓝队响应计划产出。
            alerts: 蓝队告警列表。
            ask_handler: 可选 :class:`AskHandler`；None 时使用编排器初始化时的 handler。
            severity_threshold: 触发人工复核的严重度阈值。

        Returns:
            含 ``critique`` / ``review`` 的字典。
        """
        handler = ask_handler or self._ask_handler
        # 紫队批判红队攻击链（严重度达阈值时请求人工复核）
        critique = self.critic.critique_with_human_check(
            chain.to_dict(),
            side="red",
            severity_threshold=severity_threshold,
            ask_handler=handler,
        )

        # 紫队跨产出一致性审查（保持原逻辑）
        artifacts = {
            "attack_chain": chain.to_dict(),
            "response_plan": _asdict(plan),
            "alerts": [_asdict(a) for a in alerts],
        }
        review_result = self.reviewer._run(
            f"Review consistency: {json.dumps(artifacts, default=str)}"
        )
        review = review_result.model_dump()

        return {"critique": critique, "review": review}

    # ==================================================================
    # R4.2: SDK Agent.handoffs 声明式链
    # ==================================================================

    def run_red_chain_via_handoffs(self, target_range: str) -> dict[str, Any]:
        """通过 SDK handoffs 执行红队攻击链（声明式链）。

        与 :meth:`run_red_chain` 的区别：
            - ``run_red_chain``：手动逐步 ``_run()`` + ``json.dumps`` 传递
              （固定管道的正确架构，默认路径）
            - 本方法：用 SDK ``Agent.handoffs`` 声明式串联，
              LLM 通过 ``transfer_to_*`` 工具调用触发移交，
              ``on_handoff`` 回调 + ``input_type`` 结构化参数捕获中间产出

        限制：
            - Mock 模式下 ``MockSDKModel`` 返回纯文本（非工具调用），
              LLM 不会触发 handoff，本方法回退到 ``run_red_chain``。
            - 真实 LLM 模式下可用，但 LLM 可能不按预期移交
              （需在 prompt 中强制指令）。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` 的字典。
        """
        if not _SDK_HANDOFF_AVAILABLE:
            return self.run_red_chain(target_range)

        # 构建 handoff 链上下文
        ctx = ChainContext(target_range=target_range)

        try:
            _ = self._run_red_handoff_chain(ctx, target_range)
            # 如果 handoff 链成功（LLM 驱动了移交），使用累积的产出
            if ctx.chain is not None:
                return self._context_to_red_result(ctx)
        except Exception:
            pass

        # 回退到手动链
        return self.run_red_chain(target_range)

    def run_blue_chain_via_handoffs(
        self, event_stream: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """通过 SDK handoffs 执行蓝队防御链（声明式链）。

        链路：detector → triage → threat_hunt → ir_planner

        Args:
            event_stream: 原始事件流列表。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        if not _SDK_HANDOFF_AVAILABLE:
            return self.run_blue_chain(event_stream)

        ctx = ChainContext(event_stream=event_stream)

        try:
            _ = self._run_blue_handoff_chain(ctx, event_stream)
            if ctx.plan is not None:
                return self._context_to_blue_result(ctx)
        except Exception:
            pass

        # 回退到手动链
        return self.run_blue_chain(event_stream)

    def _run_red_handoff_chain(
        self, ctx: ChainContext, target_range: str
    ) -> Any:
        """运行红队 handoff 链。

        创建 SDK Agent 并配置 handoffs，用 ``on_handoff`` 回调将
        各步产出捕获到 :class:`ChainContext`。
        """
        from agents import Runner

        # 创建轻量级 SDK Agent 用于 handoff 链
        # 每个 Agent 配置 handoffs 指向下一个 Agent
        exploit_agent = SDKAgent(
            name="ExploitPlannerAgent",
            instructions="Plan an exploit chain based on vulnerabilities. "
            "After producing your output, call transfer_to_complete to finish.",
            handoffs=[],  # 末端无 handoff
        )

        vuln_agent = SDKAgent(
            name="VulnCorrelatorAgent",
            instructions="Correlate vulnerabilities for given assets. "
            "After producing your output, call transfer_to_exploit_planner.",
            handoffs=[exploit_agent],
        )

        recon_agent = SDKAgent(
            name="ReconAgent",
            instructions=f"Scan target range {target_range}. "
            "After producing your output, call transfer_to_vuln_correlator.",
            handoffs=[vuln_agent],
        )

        # 配置 on_handoff 回调（捕获中间产出到 ChainContext）
        # 注意：on_handoff 接收 (context, input_json)，但无法访问 agent 的结构化输出
        # 因此我们用 ChainContext 累积 input_json 作为链间数据传递
        self._configure_red_handoff_callbacks(ctx, recon_agent, vuln_agent, exploit_agent)

        # 运行链——由 LLM 驱动 handoff
        return Runner.run_sync(
            recon_agent,
            f"Scan target range: {target_range}",
        )

    def _run_blue_handoff_chain(
        self, ctx: ChainContext, event_stream: list[dict[str, Any]]
    ) -> Any:
        """运行蓝队 handoff 链。

        链路：detector → triage → threat_hunt → ir_planner
        """
        from agents import Runner

        ir_agent = SDKAgent(
            name="IRPlannerAgent",
            instructions="Plan incident response actions. This is the final step.",
            handoffs=[],
        )
        hunt_agent = SDKAgent(
            name="ThreatHuntAgent",
            instructions="Generate threat hunting hypotheses. "
            "After producing your output, call transfer_to_ir_planner.",
            handoffs=[ir_agent],
        )
        triage_agent = SDKAgent(
            name="TriageAgent",
            instructions="Triage detected alerts. "
            "After producing your output, call transfer_to_threat_hunt.",
            handoffs=[hunt_agent],
        )
        detector_agent = SDKAgent(
            name="DetectorAgent",
            instructions="Detect anomalies in the event stream. "
            "After producing your output, call transfer_to_triage.",
            handoffs=[triage_agent],
        )

        self._configure_blue_handoff_callbacks(
            ctx, detector_agent, triage_agent, hunt_agent, ir_agent
        )

        return Runner.run_sync(
            detector_agent,
            f"Detect anomalies in: {json.dumps(event_stream)}",
        )

    def _configure_red_handoff_callbacks(
        self,
        ctx: ChainContext,
        recon_agent: Any,
        vuln_agent: Any,
        exploit_agent: Any,
    ) -> None:
        """配置红队 handoff 回调，捕获中间产出到 ChainContext。

        SDK ``handoff()`` 规则：
            - 不提供 ``input_type`` 时，``on_handoff`` 只接收 1 个参数 (context)
            - 提供 ``input_type`` 时，``on_handoff`` 接收 2 个参数 (context, input)

        本方法不使用 ``input_type``（因为中间产出类型不固定），
        因此 ``on_handoff`` 回调只接收 context，从 context 中读取累积的产出。
        """
        if not _SDK_HANDOFF_AVAILABLE:
            return

        def on_recon_to_vuln(wrapper: RunContextWrapper[ChainContext]) -> None:
            """recon → vuln handoff 回调：标记侦察完成。"""
            ctx.recon_output = {"status": "recon_handoff_triggered"}

        def on_vuln_to_exploit(wrapper: RunContextWrapper[ChainContext]) -> None:
            """vuln → exploit handoff 回调：标记漏洞关联完成。"""
            ctx.vuln_output = {"status": "vuln_handoff_triggered"}

        # 替换默认 handoffs 为带回调的版本
        recon_agent.handoffs = [handoff(vuln_agent, on_handoff=on_recon_to_vuln)]
        vuln_agent.handoffs = [handoff(exploit_agent, on_handoff=on_vuln_to_exploit)]

    def _configure_blue_handoff_callbacks(
        self,
        ctx: ChainContext,
        detector_agent: Any,
        triage_agent: Any,
        hunt_agent: Any,
        ir_agent: Any,
    ) -> None:
        """配置蓝队 handoff 回调，捕获中间产出到 ChainContext。"""
        if not _SDK_HANDOFF_AVAILABLE:
            return

        def on_detector_to_triage(wrapper: RunContextWrapper[ChainContext]) -> None:
            ctx.detector_output = {"status": "detector_handoff_triggered"}

        def on_triage_to_hunt(wrapper: RunContextWrapper[ChainContext]) -> None:
            ctx.triage_output = {"status": "triage_handoff_triggered"}

        def on_hunt_to_ir(wrapper: RunContextWrapper[ChainContext]) -> None:
            ctx.hunt_output = {"status": "hunt_handoff_triggered"}

        detector_agent.handoffs = [handoff(triage_agent, on_handoff=on_detector_to_triage)]
        triage_agent.handoffs = [handoff(hunt_agent, on_handoff=on_triage_to_hunt)]
        hunt_agent.handoffs = [handoff(ir_agent, on_handoff=on_hunt_to_ir)]

    def _context_to_red_result(self, ctx: ChainContext) -> dict[str, Any]:
        """将 ChainContext 转换为红队链结果字典。"""
        assets: list[Asset] = []
        findings: list[VulnFinding] = []
        chain: AttackChain | None = None

        if ctx.recon_output:
            assets = [
                Asset(
                    asset_id=a.get("asset_id", ""),
                    host=a.get("host", ""),
                    services=a.get("services", []),
                    os=a.get("os", ""),
                    exposure=a.get("exposure", "unknown"),
                )
                for a in ctx.recon_output.get("assets", [])
            ]

        if ctx.vuln_output:
            findings = [
                VulnFinding(
                    finding_id=f.get("finding_id", ""),
                    cve_id=f.get("cve_id", ""),
                    asset_id=f.get("asset_id", ""),
                    cvss=f.get("cvss", 0.0),
                    attack_surface=f.get("attack_surface", ""),
                )
                for f in ctx.vuln_output.get("findings", [])
            ]

        if ctx.exploit_output:
            exp = ctx.exploit_output
            chain = AttackChain(
                chain_id=exp.get("chain_id", ""),
                target=exp.get("target", ctx.target_range or ""),
                steps=[AttackStep(**s) for s in exp.get("steps", [])],
                status=exp.get("status", "planned"),
            )
        else:
            chain = AttackChain(
                chain_id="", target=ctx.target_range or "", steps=[], status="failed"
            )

        return {"assets": assets, "findings": findings, "chain": chain}

    def _context_to_blue_result(self, ctx: ChainContext) -> dict[str, Any]:
        """将 ChainContext 转换为蓝队链结果字典。"""
        alerts: list[Alert] = []
        triaged: list[Alert] = []
        hypotheses: list[dict] = []
        plan: ResponsePlan | None = None

        if ctx.detector_output:
            alerts = [
                Alert(
                    alert_id=a.get("alert_id", ""),
                    severity=a.get("severity", "low"),
                    src=a.get("src", ""),
                    dst=a.get("dst", ""),
                    technique=a.get("technique", ""),
                    raw=a.get("raw", {}),
                )
                for a in ctx.detector_output.get("alerts", [])
            ]

        if ctx.triage_output:
            triaged = [
                Alert(**t) for t in ctx.triage_output.get("alerts", [])
            ] or alerts

        if ctx.hunt_output:
            hypotheses = ctx.hunt_output.get("hypotheses", [])

        if ctx.ir_output:
            ir = ctx.ir_output
            plan = ResponsePlan(
                plan_id=ir.get("plan_id", ""),
                actions=ir.get("actions", []),
                confidence=ir.get("confidence", 0.0),
                rollback=ir.get("rollback", {}),
            )
        else:
            plan = ResponsePlan(
                plan_id="", actions=[], confidence=0.0, rollback={}
            )

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
        }

    # ==================================================================
    # R4.3: SDK output_guardrails 紫队校验
    # ==================================================================

    def run_red_chain_with_guardrail(
        self, target_range: str, max_retries: int = 2
    ) -> dict[str, Any]:
        """带 output_guardrail 的红队攻击链（紫队校验闭环）。

        在 exploit_planner Agent 的 ``output_guardrails`` 上注入紫队 critic 校验：
            1. 正常执行红队链（recon → vuln → exploit）
            2. exploit_planner 产出后，guardrail 校验攻击链有效性
            3. 如果 guardrail tripwire 触发（``tripwire_triggered=True``），
               SDK 抛出 ``OutputGuardrailTripwireTriggered`` 异常
            4. 捕获异常，从 ``output_info`` 提取反馈，重新执行 exploit_planner
            5. 最多重试 ``max_retries`` 次

        与 :meth:`run_red_chain` 的区别：
            - ``run_red_chain``：无校验，直接返回
            - 本方法：有 SDK guardrail 校验 + 手动重试循环

        限制：
            - SDK guardrail 抛异常后不会自动重试（需手动捕获 + 重新调用）
            - Mock 模式下 MockSDKModel 返回固定 JSON，guardrail 可能不触发

        Args:
            target_range: 目标网络范围。
            max_retries: guardrail 触发后最大重试次数（默认 2）。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` / ``guardrail_passed`` 的字典。
        """
        # 先执行 recon + vuln（不受 guardrail 影响）
        recon_result = self.recon._run(f"Scan target range: {target_range}")
        assets = [
            Asset(
                asset_id=a.asset_id, host=a.host, services=a.services, os=a.os, exposure=a.exposure
            )
            for a in recon_result.assets
        ]

        assets_desc = json.dumps(
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        vuln_result = self.vuln_correlator._run(
            f"Correlate vulnerabilities for these assets: {assets_desc}"
        )
        findings = [
            VulnFinding(
                finding_id=f.finding_id,
                cve_id=f.cve_id,
                asset_id=f.asset_id,
                cvss=f.cvss,
                attack_surface=f.attack_surface,
            )
            for f in vuln_result.findings
        ]

        findings_desc = json.dumps(
            [
                {
                    "finding_id": f.finding_id,
                    "cve_id": f.cve_id,
                    "asset_id": f.asset_id,
                    "cvss": f.cvss,
                }
                for f in findings
            ]
        )

        # 执行 exploit_planner + guardrail 重试循环
        guardrail_passed = False
        feedback = ""
        exploit_result = None

        # 注入 output_guardrail 到 exploit_planner 的 SDK Agent
        if _SDK_GUARDRAIL_AVAILABLE:
            guardrail = self.create_attack_chain_guardrail()
            if guardrail is not None:
                self.exploit_planner._sdk_agent.output_guardrails = [guardrail]

        for attempt in range(max_retries + 1):
            prompt = f"Plan exploit chain for: {findings_desc}"
            if feedback:
                prompt += f"\n\nPrevious attempt was rejected. Feedback: {feedback}"

            try:
                exploit_result = self.exploit_planner._run(prompt)
                guardrail_passed = True
                break
            except OutputGuardrailTripwireTriggered as e:
                # 从 guardrail 结果中提取反馈
                feedback = str(
                    e.guardrail_result.output.output_info
                    if e.guardrail_result and e.guardrail_result.output
                    else "Attack chain validation failed"
                )
                if attempt >= max_retries:
                    # 最后一次重试仍失败，返回未通过的结果
                    if exploit_result is None:
                        # 没有任何产出，返回空链
                        chain = AttackChain(
                            chain_id="",
                            target=target_range,
                            steps=[],
                            status="failed",
                        )
                        return {
                            "assets": assets,
                            "findings": findings,
                            "chain": chain,
                            "guardrail_passed": False,
                            "guardrail_feedback": feedback,
                        }
                    break

        # 构建最终攻击链
        if exploit_result is not None:
            chain = AttackChain(
                chain_id=exploit_result.chain_id,
                target=exploit_result.target,
                steps=[AttackStep(**s.model_dump()) for s in exploit_result.steps],
                status=exploit_result.status,
            )
        else:
            chain = AttackChain(
                chain_id="", target=target_range, steps=[], status="failed"
            )

        # 清理 guardrail（避免影响后续调用）
        if _SDK_GUARDRAIL_AVAILABLE:
            self.exploit_planner._sdk_agent.output_guardrails = []

        return {
            "assets": assets,
            "findings": findings,
            "chain": chain,
            "guardrail_passed": guardrail_passed,
            "guardrail_feedback": feedback if not guardrail_passed else "",
        }

    @staticmethod
    def create_attack_chain_guardrail() -> Any:
        """创建攻击链校验 output_guardrail。

        返回一个 :class:`OutputGuardrail`，校验 Agent 产出的攻击链是否：
            - 有至少 1 个步骤
            - 每个步骤有 technique 字段
            - chain_id 非空

        校验失败时返回 ``GuardrailFunctionOutput(tripwire_triggered=True)``，
        SDK 将抛出 ``OutputGuardrailTripwireTriggered`` 异常。

        Returns:
            :class:`OutputGuardrail` 实例；SDK 不可用时返回 None。
        """
        if not _SDK_GUARDRAIL_AVAILABLE:
            return None

        @output_guardrail(name="attack_chain_validator")
        def validate_attack_chain(
            ctx: RunContextWrapper[Any], agent: Any, agent_output: Any
        ) -> GuardrailFunctionOutput:
            """校验攻击链产出。"""
            issues: list[str] = []

            # agent_output 可能是 Pydantic 模型或 dict
            if hasattr(agent_output, "model_dump"):
                output_dict = agent_output.model_dump()
            elif isinstance(agent_output, dict):
                output_dict = agent_output
            else:
                return GuardrailFunctionOutput(
                    tripwire_triggered=True,
                    output_info="Invalid output type: expected ExploitPlannerResult",
                )

            chain_id = output_dict.get("chain_id", "")
            if not chain_id:
                issues.append("chain_id is empty")

            steps = output_dict.get("steps", [])
            if not steps:
                issues.append("attack chain has no steps")

            for i, step in enumerate(steps):
                step_dict = step if isinstance(step, dict) else step.model_dump() if hasattr(step, "model_dump") else {}
                if not step_dict.get("technique"):
                    issues.append(f"step {i} has no technique")

            if issues:
                return GuardrailFunctionOutput(
                    tripwire_triggered=True,
                    output_info="; ".join(issues),
                )

            return GuardrailFunctionOutput(
                tripwire_triggered=False,
                output_info="Attack chain validation passed",
            )

        return validate_attack_chain

    # ==================================================================
    # R4.4: SDK tracing + AgentHooks
    # ==================================================================

    def enable_tracing(self) -> CyberTraceProcessor:
        """启用 SDK tracing，返回 trace 处理器。

        创建 :class:`CyberTraceProcessor` 并注册到 SDK 全局。
        之后调用 :meth:`run_red_chain_traced` / :meth:`run_blue_chain_traced` /
        :meth:`run_purple_review_traced` 时，SDK 自动采集 trace/span 数据。

        Returns:
            :class:`CyberTraceProcessor` 实例（可通过 ``get_trace_data()`` 获取数据）。

        Raises:
            RuntimeError: SDK tracing 不可用时抛出。
        """
        if not _SDK_TRACING_AVAILABLE:
            raise RuntimeError("SDK tracing is not available")
        self._trace_processor = CyberTraceProcessor()
        set_trace_processors([self._trace_processor])
        return self._trace_processor

    def disable_tracing(self) -> None:
        """禁用 SDK tracing，清理处理器状态。"""
        if self._trace_processor is not None:
            self._trace_processor.shutdown()
            self._trace_processor = None
        # 恢复 SDK 默认 trace 处理器（空列表 = 禁用自定义处理器）
        if _SDK_TRACING_AVAILABLE:
            set_trace_processors([])

    def install_hooks(self, eventbus: Any = None, task_id: str = "") -> list[CyberAgentHooks]:
        """为所有 9 个 SDK Agent 安装生命周期钩子。

        为每个 Agent 创建 :class:`CyberAgentHooks` 并设置到 ``agent.hooks`` 属性。
        SDK Runner 执行 Agent 时自动触发回调，记录 ``on_start`` / ``on_end`` 等事件。

        R5.4：若注入 ``eventbus``，回调中还发布 :class:`protocol.Event` 到总线，
        供 ``backend/routers/sse.py`` 实时推送与 ``observability/inspect/replay/`` 回放消费。

        Args:
            eventbus: 可选的 :class:`EventBus` 实例；非 None 时钩子发布事件到总线。
            task_id: 可选的任务 ID，作为发布事件的 ``task_id`` 字段。

        Returns:
            安装的 :class:`CyberAgentHooks` 列表（9 个）。
        """
        hooked: list[StructuredAgent[Any]] = [
            self.recon,
            self.vuln_correlator,
            self.exploit_planner,
            self.detector,
            self.triage,
            self.threat_hunt,
            self.ir_planner,
            self.critic,
            self.reviewer,
        ]
        self._hooks = []
        for agent in hooked:
            hook = CyberAgentHooks(
                agent_name=agent.__class__.__name__,
                eventbus=eventbus,
                task_id=task_id,
            )
            agent._sdk_agent.hooks = hook
            self._hooks.append(hook)
        return self._hooks

    def get_hooks_events(self) -> list[dict[str, Any]]:
        """汇总所有 AgentHooks 采集的事件。

        Returns:
            事件字典列表（每个含 ``event_type`` / ``agent_name`` / ``timestamp`` / ``data``）。
        """
        events: list[dict[str, Any]] = []
        for hook in self._hooks:
            for evt in hook.events:
                events.append(evt.to_dict())
        return events

    def get_trace_data(self) -> CyberTraceData | None:
        """获取最近一次 trace 的采集数据。

        Returns:
            :class:`CyberTraceData` 实例；未启用 tracing 或无 trace 时返回 None。
        """
        if self._trace_processor is None:
            return None
        return self._trace_processor.get_trace_data()

    def get_trace_json(self) -> str | None:
        """获取最近一次 trace 的 JSON 字符串。

        Returns:
            JSON 字符串；未启用 tracing 或无 trace 时返回 None。
        """
        data = self.get_trace_data()
        if data is None:
            return None
        return data.to_json()

    def run_red_chain_traced(self, target_range: str) -> dict[str, Any]:
        """带 SDK tracing 的红队攻击链。

        用 ``trace(workflow_name="cyber_red_chain")`` 上下文管理器包裹
        :meth:`run_red_chain`，SDK 自动采集 trace/span 数据。

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` 的字典（同 :meth:`run_red_chain`）。
        """
        if not _SDK_TRACING_AVAILABLE:
            return self.run_red_chain(target_range)

        with trace(
            workflow_name="cyber_red_chain",
            metadata={"scenario": "red", "target": target_range},
        ):
            result = self.run_red_chain(target_range)
        return result

    def run_blue_chain_traced(
        self, event_stream: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """带 SDK tracing 的蓝队防御链。

        用 ``trace(workflow_name="cyber_blue_chain")`` 上下文管理器包裹
        :meth:`run_blue_chain`。

        Args:
            event_stream: 原始事件流列表。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` 的字典。
        """
        if not _SDK_TRACING_AVAILABLE:
            return self.run_blue_chain(event_stream)

        with trace(
            workflow_name="cyber_blue_chain",
            metadata={"scenario": "blue", "events": len(event_stream)},
        ):
            result = self.run_blue_chain(event_stream)
        return result

    def run_purple_review_traced(
        self, chain: AttackChain, plan: ResponsePlan, alerts: list[Alert]
    ) -> dict[str, Any]:
        """带 SDK tracing 的紫队校验。

        用 ``trace(workflow_name="cyber_purple_review")`` 上下文管理器包裹
        :meth:`run_purple_review`。

        Args:
            chain: 红队攻击链产出。
            plan: 蓝队响应计划产出。
            alerts: 蓝队告警列表。

        Returns:
            含 ``critique`` / ``review`` 的字典。
        """
        if not _SDK_TRACING_AVAILABLE:
            return self.run_purple_review(chain, plan, alerts)

        with trace(
            workflow_name="cyber_purple_review",
            metadata={
                "scenario": "purple",
                "chain_steps": len(chain.steps),
                "alert_count": len(alerts),
            },
        ):
            result = self.run_purple_review(chain, plan, alerts)
        return result

    # ==================================================================
    # R4.5: SDK FunctionTool 注册攻防工具
    # ==================================================================

    def get_red_team_tools(self) -> list[Any]:
        """获取红队 SDK FunctionTool 列表。

        红队工具：
            - ``nmap_scan``         — 网络扫描（低风险）
            - ``metasploit_exploit`` — 漏洞利用（高危，needs_approval=True）
            - ``lateral_move_exec``  — 横向移动（高危，needs_approval=True）

        Returns:
            SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
        """
        from aegisos_agents.tools.cyber_tools import create_red_team_tools

        return create_red_team_tools()

    def get_blue_team_tools(self) -> list[Any]:
        """获取蓝队 SDK FunctionTool 列表。

        蓝队工具：
            - ``query_attck_kb``    — 查询 ATT&CK 知识库
            - ``query_cve_db``      — 查询 CVE 漏洞库
            - ``correlate_alerts``  — 关联告警分析

        Returns:
            SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
        """
        from aegisos_agents.tools.cyber_tools import create_blue_team_tools

        return create_blue_team_tools()

    def get_all_cyber_tools(self) -> list[Any]:
        """获取全部攻防 SDK FunctionTool 列表（红队 + 蓝队）。

        Returns:
            SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
        """
        from aegisos_agents.tools.cyber_tools import create_all_cyber_tools

        return create_all_cyber_tools()

    def install_red_team_tools(self) -> list[Any]:
        """为红队 Agent 安装 FunctionTool。

        将红队工具注册到对应 Agent 的 SDK ``Agent.tools`` 属性：
            - ``recon`` ← ``nmap_scan``
            - ``exploit_planner`` ← ``metasploit_exploit``
            - ``exploit_planner`` ← ``lateral_move_exec``

        Returns:
            安装到 Agent 上的 FunctionTool 列表。
        """
        tools = self.get_red_team_tools()
        if not tools:
            return []

        tool_map: dict[str, list[Any]] = {
            "nmap_scan": [self.recon],
            "metasploit_exploit": [self.exploit_planner],
            "lateral_move_exec": [self.exploit_planner],
        }

        for tool in tools:
            tool_name = getattr(tool, "name", "")
            agents = tool_map.get(tool_name, [])
            for agent in agents:
                existing = list(agent._sdk_agent.tools)
                existing.append(tool)
                agent._sdk_agent.tools = existing

        return tools

    def install_blue_team_tools(self) -> list[Any]:
        """为蓝队 Agent 安装 FunctionTool。

        将蓝队工具注册到对应 Agent 的 SDK ``Agent.tools`` 属性：
            - ``detector`` ← ``correlate_alerts``
            - ``triage`` ← ``correlate_alerts``
            - ``vuln_correlator`` ← ``query_cve_db``
            - ``detector`` ← ``query_attck_kb``
            - ``threat_hunt`` ← ``query_attck_kb``

        Returns:
            安装到 Agent 上的 FunctionTool 列表。
        """
        tools = self.get_blue_team_tools()
        if not tools:
            return []

        tool_map: dict[str, list[Any]] = {
            "correlate_alerts": [self.detector, self.triage],
            "query_cve_db": [self.vuln_correlator],
            "query_attck_kb": [self.detector, self.threat_hunt],
        }

        for tool in tools:
            tool_name = getattr(tool, "name", "")
            agents = tool_map.get(tool_name, [])
            for agent in agents:
                existing = list(agent._sdk_agent.tools)
                existing.append(tool)
                agent._sdk_agent.tools = existing

        return tools

    def install_all_tools(self) -> list[Any]:
        """为所有 Agent 安装攻防 FunctionTool（红队 + 蓝队）。

        Returns:
            全部安装的 FunctionTool 列表。
        """
        red = self.install_red_team_tools()
        blue = self.install_blue_team_tools()
        return red + blue

    def uninstall_all_tools(self) -> None:
        """从所有 Agent 移除已安装的 FunctionTool。

        将所有 Agent 的 ``Agent.tools`` 重置为空列表。
        """
        cleared: list[StructuredAgent[Any]] = [
            self.recon,
            self.vuln_correlator,
            self.exploit_planner,
            self.detector,
            self.triage,
            self.threat_hunt,
            self.ir_planner,
            self.critic,
            self.reviewer,
        ]
        for agent in cleared:
            agent._sdk_agent.tools = []

    def get_agent_tools(self, agent_name: str) -> list[Any]:
        """获取指定 Agent 已安装的 FunctionTool 列表。

        Args:
            agent_name: Agent 属性名（如 ``"recon"`` / ``"detector"``）。

        Returns:
            该 Agent 上已安装的 FunctionTool 列表。
        """
        agent = getattr(self, agent_name, None)
        if agent is None:
            return []
        return list(agent._sdk_agent.tools)

    def get_high_risk_tools(self) -> list[Any]:
        """获取需要审批的高危工具列表。

        高危工具（``needs_approval=True``）：
            - ``metasploit_exploit``
            - ``lateral_move_exec``

        Returns:
            高危 FunctionTool 列表。
        """
        all_tools = self.get_all_cyber_tools()
        return [t for t in all_tools if getattr(t, "needs_approval", False)]

    # ==================================================================
    # AP3: Goal 范式（递归目标分解 + 失败重试 + 备选路径）
    # ==================================================================

    # date: 2026-07-08
    # dev: myf
    # changelog: AP3.2 CyberOrchestrator 接入 Goal--新增 run_red_chain_with_goal / run_blue_chain_with_goal / _create_red_agent_executor / _create_blue_agent_executor 方法

    def run_red_chain_with_goal(
        self,
        target_range: str,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Goal 范式执行红队攻击链（递归目标分解 + 失败重试）。

        替代 :meth:`run_red_chain` 的固定模板链，将目标分解为子目标树：
            recon -> vuln_correlator -> exploit_planner -> lateral_move

        每个子目标由对应 Agent 执行，失败时自动重试（最多 max_retries 次），
        重试时注入 fallback 备选路径提示。最终汇聚所有子目标产出。

        与 :meth:`run_red_chain` 的区别：
            - ``run_red_chain``：固定模板，无重试，单次执行
            - 本方法：递归分解，失败重试 + 备选路径，更鲁棒

        Args:
            target_range: 目标网络范围，如 ``"10.0.0.0/24"``。
            max_retries: 子目标失败后的最大重试次数。

        Returns:
            含 ``assets`` / ``findings`` / ``chain`` / ``goal_result`` 的字典。
            ``goal_result`` 是 :class:`GoalResult`，含子目标执行状态。
        """
        tree = self.decompose(
            f"攻击 {target_range}",
            scenario="cyber_red",
        )
        executor = self._create_red_agent_executor(target_range)
        result = self.execute_tree(tree, executor, max_retries=max_retries)

        # 汇聚产出
        assets = result.outputs.get("recon", [])
        findings = result.outputs.get("vuln", [])
        chain = result.outputs.get("exploit", AttackChain(
            chain_id="", target=target_range, steps=[], status="failed"
        ))

        return {
            "assets": assets,
            "findings": findings,
            "chain": chain,
            "goal_result": result,
        }

    def run_blue_chain_with_goal(
        self,
        event_stream: list[dict[str, Any]],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Goal 范式执行蓝队防御链（递归目标分解 + 失败重试）。

        替代 :meth:`run_blue_chain` 的固定模板链，将目标分解为子目标树：
            detector -> triage -> threat_hunt -> ir_planner

        每个子目标由对应 Agent 执行，失败时自动重试。

        Args:
            event_stream: 原始事件流列表。
            max_retries: 子目标失败后的最大重试次数。

        Returns:
            含 ``alerts`` / ``triaged`` / ``hypotheses`` / ``plan`` / ``goal_result`` 的字典。
        """
        tree = self.decompose(
            "防御事件流",
            scenario="cyber_blue",
        )
        executor = self._create_blue_agent_executor(event_stream)
        result = self.execute_tree(tree, executor, max_retries=max_retries)

        alerts = result.outputs.get("detect", [])
        triaged = result.outputs.get("triage", alerts)
        hypotheses = result.outputs.get("hunt", [])
        plan = result.outputs.get("respond", ResponsePlan(
            plan_id="", actions=[], confidence=0.0, rollback={}
        ))

        return {
            "alerts": alerts,
            "triaged": triaged,
            "hypotheses": hypotheses,
            "plan": plan,
            "goal_result": result,
        }

    def _create_red_agent_executor(
        self, target_range: str
    ) -> Any:
        """创建红队子目标执行回调。

        返回一个 ``executor(node, context) -> Any`` 回调，根据 ``node.agent_name``
        调用对应的红队 Agent，并将上游产出注入为上下文。

        Args:
            target_range: 目标网络范围。

        Returns:
            执行回调函数。
        """

        def executor(node: GoalNode, context: dict[str, Any]) -> Any:
            """红队子目标执行器。

            根据 node.agent_name 分发到对应 Agent，上游产出从 context 中获取。
            失败时抛出异常，由 :meth:`GoalMode.execute_tree` 捕获并重试。
            """
            agent_name = node.agent_name
            fallback_hint = context.get("_fallback_hint", "")

            # P3.2: 低熵稀疏路由前置守卫 —— 目标 Agent 必须在 Top-K 内才执行
            try:
                self.assert_target_routable(agent_name, agent_name)
            except ValueError:
                # 单候选能力（如 lateral_move）路由可能为空；只有当图里无该
                # capability 节点时才放行（启动时未注入该 Agent 的场景）
                if any(
                    n.node_id == agent_name
                    for n in self._topology.nodes.values()
                ):
                    raise

            if agent_name == "recon":
                prompt = f"Scan target range: {target_range}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                recon_result = self.recon._run(prompt)
                return [
                    Asset(
                        asset_id=a.asset_id,
                        host=a.host,
                        services=a.services,
                        os=a.os,
                        exposure=a.exposure,
                    )
                    for a in recon_result.assets
                ]

            elif agent_name == "vuln_correlator":
                assets = context.get("recon", [])
                assets_desc = json.dumps(
                    [
                        {
                            "asset_id": a.asset_id,
                            "host": a.host,
                            "services": a.services,
                            "os": a.os,
                        }
                        for a in assets
                    ]
                )
                prompt = f"Correlate vulnerabilities for these assets: {assets_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                vuln_result = self.vuln_correlator._run(prompt)
                return [
                    VulnFinding(
                        finding_id=f.finding_id,
                        cve_id=f.cve_id,
                        asset_id=f.asset_id,
                        cvss=f.cvss,
                        attack_surface=f.attack_surface,
                    )
                    for f in vuln_result.findings
                ]

            elif agent_name == "exploit_planner":
                findings = context.get("vuln", [])
                findings_desc = json.dumps(
                    [
                        {
                            "finding_id": f.finding_id,
                            "cve_id": f.cve_id,
                            "asset_id": f.asset_id,
                            "cvss": f.cvss,
                        }
                        for f in findings
                    ]
                )
                prompt = f"Plan exploit chain for: {findings_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                exploit_result = self.exploit_planner._run(prompt)
                return AttackChain(
                    chain_id=exploit_result.chain_id,
                    target=exploit_result.target,
                    steps=[
                        AttackStep(**s.model_dump()) for s in exploit_result.steps
                    ],
                    status=exploit_result.status,
                )

            elif agent_name == "lateral_move":
                from aegisos_agents.action.lateral_move.agent import LateralMoveAgent

                chain = context.get("exploit", AttackChain(chain_id=""))
                lateral_agent = LateralMoveAgent(
                    mock=self._mock,
                )
                prompt = f"Plan lateral moves. Chain: {json.dumps(chain.to_dict() if hasattr(chain, 'to_dict') else {})}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                lateral_result = lateral_agent._run(prompt)
                return [
                    AttackStep(**s.model_dump()) for s in lateral_result.steps
                ]

            else:
                raise ValueError(f"Unknown red team agent: {agent_name}")

        return executor

    def _create_blue_agent_executor(
        self, event_stream: list[dict[str, Any]]
    ) -> Any:
        """创建蓝队子目标执行回调。

        Args:
            event_stream: 原始事件流列表。

        Returns:
            执行回调函数。
        """

        def executor(node: GoalNode, context: dict[str, Any]) -> Any:
            """蓝队子目标执行器。"""
            agent_name = node.agent_name
            fallback_hint = context.get("_fallback_hint", "")

            # P3.2: 低熵稀疏路由前置守卫（与红队一致）
            try:
                self.assert_target_routable(agent_name, agent_name)
            except ValueError:
                if any(
                    n.node_id == agent_name
                    for n in self._topology.nodes.values()
                ):
                    raise

            if agent_name == "detector":
                prompt = f"Detect anomalies in: {json.dumps(event_stream)}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                detector_result = self.detector._run(prompt)
                return [
                    Alert(
                        alert_id=a.alert_id,
                        severity=a.severity,
                        src=a.src,
                        dst=a.dst,
                        technique=a.technique,
                        raw=a.raw,
                    )
                    for a in detector_result.alerts
                ]

            elif agent_name == "triage":
                alerts = context.get("detect", [])
                alerts_desc = json.dumps(
                    [
                        {
                            "alert_id": a.alert_id,
                            "severity": a.severity,
                            "src": a.src,
                            "dst": a.dst,
                        }
                        for a in alerts
                    ]
                )
                prompt = f"Triage these alerts: {alerts_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                triage_result = self.triage._run(prompt)
                return [
                    Alert(**t.model_dump()) for t in triage_result.alerts
                ] or alerts

            elif agent_name == "threat_hunt":
                alerts = context.get("triage", context.get("detect", []))
                alerts_desc = json.dumps(
                    [
                        {"alert_id": a.alert_id, "severity": a.severity}
                        for a in alerts
                    ]
                )
                prompt = f"Generate hunting hypotheses for: {alerts_desc}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                hunt_result = self.threat_hunt._run(prompt)
                return [h.model_dump() for h in hunt_result.hypotheses]

            elif agent_name == "ir_planner":
                hypotheses = context.get("hunt", [])
                prompt = f"Plan response for: {json.dumps(hypotheses)}"
                if fallback_hint:
                    prompt += f" (Fallback: {fallback_hint})"
                ir_result = self.ir_planner._run(prompt)
                return ResponsePlan(
                    plan_id=ir_result.plan_id,
                    actions=[
                        DefenseAction.model_validate(a.model_dump())
                        for a in ir_result.actions
                    ],
                    confidence=ir_result.confidence,
                    rollback=ir_result.rollback,
                )

            else:
                raise ValueError(f"Unknown blue team agent: {agent_name}")

        return executor

    # ==================================================================
    # CyberDrill(R1)：多轮收敛演练主循环
    # ==================================================================

    @staticmethod
    def _synthesize_event_stream(
        chain: AttackChain,
        prev_event_stream: list[dict[str, Any]],
        round: int,
    ) -> list[dict[str, Any]]:
        """跨轮事件合成：把红队攻击链步骤翻译为蓝队可消费的"事件流"。

        R18（真实模型修复）：
        1. 去重键从 step_id 改为步骤内容指纹（from,to,technique）——真实 LLM
           每轮重新编号 S-001..N 但内容全新，按 step_id 去重会把新链误判为
           "无新增"（假 no_progress 收敛）。mock 链内容稳定，两种键行为一致。
        2. 事件流不再跨轮 carry 旧事件：蓝队告警必须与本轮攻击链同源，
           否则紫队 reviewer 拿旧事件告警对比新链必然判不一致（drill-e7ada3a1
           的 R2-R5 consistent=False 根因）。跨轮上下文已由 R8 记忆摘要与
           critique_feedback 承载，无需旧事件。

        Args:
            chain: 本轮红队攻击链。
            prev_event_stream: 上一轮合成的事件流（R18 起不再 carry，仅保持签名兼容）。
            round: 当前演练轮次。

        Returns:
            事件流列表（仅本轮链步骤）。
        """
        events: list[dict[str, Any]] = []
        for i, step in enumerate(chain.steps):
            events.append(
                {
                    "round": round,
                    "seq": i,
                    "type": "attack_step",
                    "source": step.from_asset,
                    "target": step.to_asset,
                    "technique": step.technique,
                    "success": step.success,
                    "step_id": step.step_id,
                    "carry_forward": False,
                }
            )
        return events

    @staticmethod
    def _step_fingerprint(step: AttackStep) -> tuple:
        """步骤内容指纹（R18）：真实 LLM 每轮重新编号 step_id，内容才是事实。"""
        return (
            (step.from_asset or "").strip().lower(),
            (step.to_asset or "").strip().lower(),
            (step.technique or "").strip().lower(),
        )

    @classmethod
    def _diff_chain_steps(
        cls, prev_chain: AttackChain | None, new_chain: AttackChain
    ) -> list[AttackStep]:
        """对比上一轮与本轮，返回本轮新增的步骤（R18：按步骤内容指纹去重）。

        真实 LLM 每轮输出相同的 step_id（S-001..N）但内容全新，旧版按 step_id
        去重会把全新链误判为"无新增"；mock 链内容稳定，两种键行为一致。
        """
        prev_fps = {cls._step_fingerprint(s) for s in prev_chain.steps} if prev_chain else set()
        return [s for s in new_chain.steps if cls._step_fingerprint(s) not in prev_fps]

    @classmethod
    def _evaluate_stop(
        cls,
        round: int,
        max_rounds: int,
        new_steps: list[AttackStep],
        purple_critique_valid: bool,
        consecutive_no_new: int,
        aborted: bool = False,
    ) -> tuple[bool, str]:
        """证据驱动收敛判定（R1 评审修订：不依赖恒真的 valid/consistent）。

        任一条件满足即停止，按优先级（R18b 修订：真收敛优先于轮次上限）：
        1. 显式中止         → ``aborted``
        2. 本轮无新步骤且紫队 valid → ``converged``（多轮对抗后攻击链自洽；
           即使恰好发生在最后一轮也应报告收敛，不得被 max_rounds 掩盖——
           "第 M 轮收敛"与"打满 M 轮未收敛"是两种完全不同的结论）
        3. 达到轮次上限 M    → ``max_rounds``
        4. 连续 ≥2 轮无新步骤 → ``no_progress``（红队挖不出新证据，避免空转）
        其余继续。

        Args:
            round: 当前轮次。
            max_rounds: 轮次上限 M。
            new_steps: 本轮红队新增步骤列表。
            purple_critique_valid: 本轮紫队批判是否有缺口（valid）。
            consecutive_no_new: 已连续几轮无新步骤（含本轮）。
            aborted: 是否被显式中止。

        Returns:
            ``(should_stop, convergence_code)``。
        """
        if aborted:
            return True, "aborted"
        if not new_steps and purple_critique_valid:
            return True, "converged"
        if round >= max_rounds:
            return True, "max_rounds"
        if not new_steps and consecutive_no_new >= 2:
            return True, "no_progress"
        return False, "running"

    def run_drill(
        self,
        target_range: str,
        max_rounds: int = 5,
        on_round=None,
        abort=None,
        drill_id: str | None = None,
        memory: "MemoryStore | None" = None,
        memory_budget: int = 512,
    ) -> dict[str, Any]:
        """多轮收敛演练主循环（CyberDrill R1 / R8）。

        在每轮内依次执行红(``run_red_chain``) → 蓝(``run_blue_chain``) →
        紫(``run_purple_review``)，以证据驱动判定是否提前收敛，最多 M 轮。
        每轮结果经 ``on_round`` 回调回传（供 R3 路由喂 SSE），显式中止经
        ``abort()`` 可调用对象查询。

        R8（跨轮记忆与上下文压缩）：传入 ``memory`` 时，每轮紫队评审结束后
        将该轮 critique/review 要点写入记忆（``MemoryPacket(kind="decision")``
        路由到工作记忆 + 情景记忆），并用 ``MemoryStore.compress`` 在工作记忆
        栈上按 token 预算压缩，生成下一轮紫队的 ``prior_rounds_summary`` 摘要
        （决策保留 + 最近保留 + 其余 digest），实现跨轮上下文连续性。摘要
        轨迹写入总结报告的 ``memory_trace``。默认 memory=None 保持旧行为。

        Args:
            target_range: 目标网络范围。
            max_rounds: 轮次上限，默认 5。
            on_round: 可选回调 ``on_round(round_data: dict, round_idx: int)``，
                      每轮完成后调用（同步）。
            abort: 可选可调用对象 ``abort() -> bool``；返回 True 表示应中止。
            drill_id: 可选演练 ID；None 时按目标范围自动生成
                （``drill_<target_range 去斜杠>``）。由路由层传入可保证
                registry / 落盘文件 / SSE 事件三者 ID 一致。
            memory: 可选记忆存储；传入时启用跨轮记忆与上下文压缩（R8）。
            memory_budget: 工作记忆压缩的 token 预算，默认 512。

        Returns:
            含 ``drill_id`` / ``rounds_executed`` / ``convergence_code`` /
            ``rounds``(逐轮记录) / ``summary`` 的字典；启用记忆时每轮记录含
            ``prior_rounds_summary`` 字段，summary 含 ``memory_trace``。
        """
        if max_rounds < 1:
            max_rounds = 1
        drill_id = drill_id or f"drill_{target_range.replace('/', '_')}"
        prev_chain: AttackChain | None = None
        prev_event_stream: list[dict[str, Any]] = []
        consecutive_no_new = 0
        rounds: list[dict[str, Any]] = []
        memory_trace: list[dict[str, Any]] = []
        prior_rounds_summary: str | None = None
        code = "running"
        critique_feedback: str | None = None

        for r in range(1, max_rounds + 1):
            # 中止检查点 1：轮开始前——abort 后立即停止，不再启动新一轮
            if callable(abort) and abort():
                code = "aborted"
                break
            # 红队攻击（r>=2 触发 mock 按轮演化）；agent 调用边界亦检查 abort
            try:
                red = self.run_red_chain(
                    target_range,
                    round=r if r >= 2 else None,
                    abort=abort if callable(abort) else None,
                    critique_feedback=critique_feedback,
                )
            except DrillAborted:
                code = "aborted"
                break
            chain: AttackChain = red["chain"]
            new_steps = self._diff_chain_steps(prev_chain, chain)
            consecutive_no_new = 0 if new_steps else consecutive_no_new + 1

            # 中止检查点 2：红队阶段后——跳过蓝/紫，保留已完成的红队产物
            if callable(abort) and abort():
                code = "aborted"
                break

            # 事件合成：首轮全量，后续 carry 增量
            event_stream = self._synthesize_event_stream(
                chain, prev_event_stream, r
            )

            # 蓝队防御（失败兜底：单阶段弱化不中断整场演练，战报标记 ok=false）
            try:
                blue = self.run_blue_chain(
                    event_stream,
                    abort=abort if callable(abort) else None,
                )
                blue_ok: bool = True
                blue_error: str | None = None
            except DrillAborted:
                code = "aborted"
                break
            except Exception as exc:  # noqa: BLE001
                blue = {
                    "alerts": [],
                    "triaged": [],
                    "hypotheses": [],
                    "plan": ResponsePlan(
                        plan_id="degraded", actions=[], confidence=0.0, rollback=[]
                    ),
                }
                blue_ok = False
                blue_error = str(exc)

            # 中止检查点 3：蓝队阶段后——跳过紫队评审
            if callable(abort) and abort():
                code = "aborted"
                break

            # 紫队评审（显式传入轮次以触发按轮演化；R8 附加跨轮记忆摘要）
            try:
                purple = self.run_purple_review(
                    chain=chain,
                    plan=blue["plan"],
                    alerts=blue["alerts"],
                    round=r,
                    prior_rounds_summary=prior_rounds_summary,
                    abort=abort if callable(abort) else None,
                    assets=red.get("assets"),
                )
            except DrillAborted:
                code = "aborted"
                break
            critique = purple["critique"]
            valid = bool(critique.get("valid"))
            # R16：把本轮紫队 issues 摘要存为下一轮红队的反馈（驱动演化闭环；
            # 只看反馈必要信息，控制 token，避免把全场历史都塞给 exploit）
            if critique_feedback or (critique.get("issues") and not valid):
                _issues = critique.get("issues") or []
                _fb_lines = [f"- {i}" for i in _issues[:4]]
                critique_feedback = (
                    " ".join(_fb_lines)[:800] if _fb_lines else None
                )

            should_abort = bool(abort() if callable(abort) else False)
            stop, code = self._evaluate_stop(
                round=r,
                max_rounds=max_rounds,
                new_steps=new_steps,
                purple_critique_valid=valid,
                consecutive_no_new=consecutive_no_new,
                aborted=should_abort,
            )

            round_data = {
                "round": r,
                "red": {
                    "ok": True,
                    "assets": [a.asset_id for a in red["assets"]],
                    "finding_count": len(red["findings"]),
                    "steps": [s.to_dict() for s in chain.steps],
                    "new_steps": [s.to_dict() for s in new_steps],
                    "agent_trace": red.get("agent_trace", []),
                },
                "blue": {
                    "ok": blue_ok,
                    "error": blue_error,
                    "alerts": [_asdict(a) for a in blue["alerts"]],
                    "triaged_count": len(blue["triaged"]),
                    "hypotheses": blue.get("hypotheses", []),
                    "plan": _asdict(blue["plan"]),
                    "agent_trace": blue.get("agent_trace", []),
                },
                "purple": {
                    "ok": True,
                    "critique": critique,
                    "review": purple["review"],
                    "converged": stop,
                    "valid": valid,
                    "new_issue_count": len(critique.get("issues", []) or []),
                    "agent_trace": purple.get("agent_trace", []),
                },
                "event_stream": event_stream,
                "convergence_code": code,
                # R10: 端-边-云阶段 placement 标注（红/蓝/紫执行位置，随轮次自适应）
                "phase": self._phase_placements(r),
            }
            if memory is not None:
                round_data["prior_rounds_summary"] = prior_rounds_summary
            rounds.append(round_data)
            if callable(on_round):
                on_round(round_data, r)

            # R8: 跨轮记忆——写本轮决策 → 压缩工作记忆 → 生成下一轮摘要
            if memory is not None:
                prior_rounds_summary = self._store_round_memory(
                    memory=memory,
                    drill_id=drill_id,
                    round_no=r,
                    round_data=round_data,
                    budget=memory_budget,
                    trace=memory_trace,
                )

            prev_chain = chain
            prev_event_stream = event_stream

            if stop:
                break

        summary = {
            "conclusion": (
                "多轮红蓝紫对抗后达成收敛：攻击链覆盖全部暴露面并通过紫队一致性校验。"
                if rounds and rounds[-1]["purple"]["valid"] and code == "converged"
                else "演练在到达停止条件时结束（见 convergence_code）。"
            ),
            "convergence_code": code,
            "rounds_executed": len(rounds),
        }
        if memory is not None:
            summary["memory_trace"] = memory_trace

        return {
            "drill_id": drill_id,
            "rounds_executed": len(rounds),
            "convergence_code": code,
            "rounds": rounds,
            "summary": summary,
        }

    # ---- R10: 演练阶段 placement（端-边-云自适应调度标注）辅助 ----

    def _phase_placements(self, round_no: int | None = None) -> dict[str, dict[str, Any]]:
        """为演练红/蓝/紫三阶段标注执行位置（R10 自适应调度）。

        两重自适应：
            1. 轮次负载缩放——随对抗收敛、增量负载下降，延迟预算收紧，
               部分阶段自动卸载到更近的层（如紫队评审云→边、蓝队防御边→端）；
            2. 可执行层约束——mock 模式三层候选池齐全按调度规则选层；真实模式
               当前仅云 API 可执行（端/边暂未接独立 API），偏好层不可执行时
               降级云侧执行并在理由中说明。

        Args:
            round_no: 当前轮次（>=1）；None 视为第 1 轮（保持旧行为）。

        Returns:
            形如 ``{"red": {...}, "blue": {...}, "purple": {...}}``
            的 placement 映射，每项含 ``tier`` / ``model_id`` / ``reason``。
        """
        placements: dict[str, dict[str, Any]] = {}
        round_no = round_no or 1
        # 收敛加速：对抗收敛后增量负载快速下降（第 2 轮约 45%、第 3 轮起 30%），
        # 延迟预算随之收紧 → 部分阶段自动卸载到更近的层（紫队云→边、蓝队边→端）
        scale = max(0.3, 1.0 - 0.55 * (round_no - 1))
        executable = self._executable_tiers()
        for phase, feat in _DRILL_PHASE_FEATURES.items():
            task = Task(
                goal=feat["goal"],
                latency_budget=feat["latency_budget"] * scale,
                privacy=feat["privacy"],
            )
            try:
                preferred = schedule(
                    task, _DRILL_MODEL_POOL, required_capability=feat["capability"]
                )
            except ValueError:
                preferred = None
            if preferred is None:
                tier, model_id = "cloud", "cloud_gpu"
                reason = f"{feat['reason']} → {_DRILL_TIER_SEMANTICS['cloud']}（候选池缺失，云侧兑底）"
            elif preferred.tier in executable:
                tier, model_id = preferred.tier, preferred.model_id
                reason = f"{feat['reason']} → {_DRILL_TIER_SEMANTICS[tier]}"
            else:
                tier, model_id = "cloud", "cloud_gpu"
                reason = (
                    f"{feat['reason']} → {_DRILL_TIER_SEMANTICS[preferred.tier]}；"
                    "当前仅云 API 可执行，端/边按需降级云侧执行"
                )
            if scale < 1.0:
                reason += f"（第 {round_no} 轮负载 {int(round(scale * 100))}%，收敛加速卸载）"
            placements[phase] = {"tier": tier, "model_id": model_id, "reason": reason}
        return placements

    @staticmethod
    def _executable_tiers() -> list[str]:
        """当前可执行层级：mock 全层可用；真实模式仅云 API（端/边暂未接独立 API）。"""
        use_mock = os.getenv("AEGIS_USE_MOCK", "").lower()
        if use_mock in ("1", "true", "yes") or not os.getenv("OPENAI_API_KEY"):
            return ["device", "edge", "cloud"]
        return ["cloud"]

    # ---- R8: 跨轮记忆与上下文压缩辅助 ----

    def _store_round_memory(
        self,
        memory: "MemoryStore",
        drill_id: str,
        round_no: int,
        round_data: dict[str, Any],
        budget: int,
        trace: list[dict[str, Any]],
    ) -> str | None:
        """写本轮决策记忆并按预算压缩，返回供下一轮使用的摘要文本（R8）。

        1. 构造 ``MemoryPacket(kind="decision")``（携带本轮 critique 要点），
           ``MemoryStore.write`` 自动路由到工作记忆 + 情景记忆，并触发反思预评估；
           同时写入一条 ``kind="normal"`` 的细节包（全量 review 文本），供
           compactor 在超预算时合并为 digest——决策保留 + 细节压缩，控制 token。
        2. ``MemoryStore.compress(session_id, budget)`` 在工作记忆栈上按
           token 预算压缩：决策/最近记忆保留，其余（细节包）合并为 digest
           （溯源 task_id 列表）。
        3. 将压缩结果拼装为摘要文本（digest 标注被压缩条数），追加到 trace
           （每轮一条：stored_task_id + next_round_summary），供总结报告展示。

        Args:
            memory: 记忆存储实例。
            drill_id: 演练 ID（兼作记忆 session_id）。
            round_no: 当前轮次。
            round_data: 本轮战报（red/blue/purple 三色）。
            budget: 压缩 token 预算。
            trace: 记忆轨迹列表（原地追加）。

        Returns:
            下一轮紫队的 ``prior_rounds_summary`` 文本；无可用摘要时返回 None。
        """
        purple = round_data["purple"]
        critique = purple["critique"]
        summary_text = (
            f"round {round_no}: valid={purple['valid']} "
            f"new_issues={purple['new_issue_count']} code={round_data['convergence_code']} "
            f"findings={len(round_data['red']['steps'])} alerts={len(round_data['blue']['alerts'])}"
        )
        # 1) 核心决策包：压缩时保留，自动路由到情景记忆（历史经验）
        decision_packet = MemoryPacket(
            session_id=drill_id,
            task_id=f"{drill_id}:r{round_no}",
            kind="decision",
            summary=summary_text,
            working={
                "round": round_no,
                "critique_valid": purple["valid"],
                "new_issue_count": purple["new_issue_count"],
                "convergence_code": round_data["convergence_code"],
                "critique": critique,
            },
            episodic={
                "round": round_no,
                "attack_steps": len(round_data["red"]["steps"]),
                "new_steps": len(round_data["red"]["new_steps"]),
                "alerts": len(round_data["blue"]["alerts"]),
                "triaged": round_data["blue"]["triaged_count"],
            },
        )
        memory.write(decision_packet)
        # 2) 细节包：normal 类，超预算时被 compactor 合并为 digest
        _issues = critique.get("issues", []) or []
        issue_ids = [i.get("id", "?") if isinstance(i, dict) else str(i) for i in _issues]
        detail_packet = MemoryPacket(
            session_id=drill_id,
            task_id=f"{drill_id}:r{round_no}:detail",
            kind="normal",
            summary=(
                f"round {round_no} detail: "
                f"consistent={purple['review'].get('consistent')} "
                f"issues={issue_ids}"
            ),
            working={"review": purple["review"]},
        )
        memory.write(detail_packet)

        compressed = memory.compress(drill_id, budget)
        parts: list[str] = []
        for m in compressed:
            if m.kind == "digest":
                count = m.compression.get("count", 0)
                parts.append(f"[digest x{count}] {m.summary}")
            elif m.summary:
                parts.append(m.summary)
        next_summary = " || ".join(parts) if parts else None

        trace.append(
            {
                "round": round_no,
                "stored_task_id": decision_packet.task_id,
                "packet_summary": summary_text,
                "compressed_count": len(compressed),
                "next_round_summary": next_summary,
            }
        )
        return next_summary
