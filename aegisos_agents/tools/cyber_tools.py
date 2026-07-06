# date: 2026-07-09
# dev: myf
"""R4.5: SDK FunctionTool 攻防工具注册。

将攻防工具注册为 SDK ``FunctionTool``，LLM 可自主调用。
当前为 Mock 实现（返回模拟数据），沙箱执行依赖 H1（后移 P3）。

工具清单：
    红队工具：
        - ``nmap_scan``         — 扫描目标网段，返回资产列表
        - ``metasploit_exploit`` — 执行漏洞利用（高危，needs_approval=True）
        - ``lateral_move_exec``  — 横向移动执行（高危，needs_approval=True）

    蓝队工具：
        - ``query_attck_kb``    — 查询 ATT&CK 知识库
        - ``query_cve_db``      — 查询 CVE 漏洞库
        - ``correlate_alerts``  — 关联告警

设计要点：
    - 用 ``FunctionTool(name, description, params_json_schema, on_invoke_tool)``
      直接构造，LLM 通过 tool_call 触发 → 回调执行 → 结果返回
    - ``on_invoke_tool`` 回调签名为 ``async (ctx, raw_json) -> Any``
    - 高危操作设 ``needs_approval=True``，编排器审批后才执行
    - Mock 实现：根据输入参数返回预置结构化数据
"""

from __future__ import annotations

import json
from typing import Any

# SDK FunctionTool 依赖
try:
    from agents import FunctionTool
    from agents.tool_context import ToolContext

    _SDK_FUNCTION_TOOL_AVAILABLE = True
except ImportError:
    _SDK_FUNCTION_TOOL_AVAILABLE = False


# ==================================================================
# Mock 工具回调实现
# ==================================================================


async def _nmap_scan_callback(ctx: ToolContext, raw_input: str) -> str:
    """``nmap_scan`` 工具回调 —— Mock 扫描结果。

    Args:
        ctx: SDK ToolContext。
        raw_input: JSON 字符串，含 ``target_range`` 字段。

    Returns:
        JSON 字符串，含扫描到的资产列表。
    """
    try:
        params = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        params = {"target_range": "unknown"}

    target = params.get("target_range", "10.0.0.0/24")

    # Mock 资产数据
    assets = [
        {
            "asset_id": "asset-001",
            "host": "10.0.0.5",
            "services": ["ssh:22", "http:80"],
            "os": "Linux",
            "exposure": "external",
        },
        {
            "asset_id": "asset-002",
            "host": "10.0.0.10",
            "services": ["rdp:3389", "smb:445"],
            "os": "Windows",
            "exposure": "internal",
        },
    ]
    return json.dumps({"target_range": target, "assets": assets})


async def _metasploit_exploit_callback(ctx: ToolContext, raw_input: str) -> str:
    """``metasploit_exploit`` 工具回调 —— Mock 漏洞利用结果。

    Args:
        ctx: SDK ToolContext。
        raw_input: JSON 字符串，含 ``cve_id`` 和 ``target_host`` 字段。

    Returns:
        JSON 字符串，含利用结果（success/session_id）。
    """
    try:
        params = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        params = {}

    cve_id = params.get("cve_id", "CVE-unknown")
    target_host = params.get("target_host", "10.0.0.5")

    return json.dumps(
        {
            "cve_id": cve_id,
            "target_host": target_host,
            "success": True,
            "session_id": "session-001",
            "payload": "meterpreter/reverse_tcp",
        }
    )


async def _lateral_move_exec_callback(ctx: ToolContext, raw_input: str) -> str:
    """``lateral_move_exec`` 工具回调 —— Mock 横向移动结果。

    Args:
        ctx: SDK ToolContext。
        raw_input: JSON 字符串，含 ``from_host`` / ``to_host`` / ``technique`` 字段。

    Returns:
        JSON 字符串，含移动结果。
    """
    try:
        params = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        params = {}

    from_host = params.get("from_host", "10.0.0.5")
    to_host = params.get("to_host", "10.0.0.10")
    technique = params.get("technique", "T1021")

    return json.dumps(
        {
            "from_host": from_host,
            "to_host": to_host,
            "technique": technique,
            "success": True,
            "access_level": "admin",
        }
    )


async def _query_attck_kb_callback(ctx: ToolContext, raw_input: str) -> str:
    """``query_attck_kb`` 工具回调 —— Mock ATT&CK 知识库查询。

    Args:
        ctx: SDK ToolContext。
        raw_input: JSON 字符串，含 ``technique_id`` 字段。

    Returns:
        JSON 字符串，含技术详情。
    """
    try:
        params = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        params = {}

    technique_id = params.get("technique_id", "T1046")

    # Mock ATT&CK 知识库
    attck_kb: dict[str, dict[str, Any]] = {
        "T1046": {
            "name": "Network Service Scanning",
            "tactic": "Discovery",
            "description": "Adversaries may attempt to get a listing of services on remote hosts.",
        },
        "T1021": {
            "name": "Remote Services",
            "tactic": "Lateral Movement",
            "description": "Use remote services to gain access to internal systems.",
        },
        "T1059": {
            "name": "Command and Scripting Interpreter",
            "tactic": "Execution",
            "description": "Execute commands via scripting interpreters.",
        },
    }
    result = attck_kb.get(technique_id, {"error": f"Unknown technique: {technique_id}"})
    return json.dumps(result)


async def _query_cve_db_callback(ctx: ToolContext, raw_input: str) -> str:
    """``query_cve_db`` 工具回调 —— Mock CVE 漏洞库查询。

    Args:
        ctx: SDK ToolContext。
        raw_input: JSON 字符串，含 ``cve_id`` 字段。

    Returns:
        JSON 字符串，含 CVE 详情。
    """
    try:
        params = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        params = {}

    cve_id = params.get("cve_id", "CVE-2024-0001")

    # Mock CVE 库
    cve_db: dict[str, dict[str, Any]] = {
        "CVE-2024-0001": {
            "cve_id": "CVE-2024-0001",
            "cvss": 9.8,
            "description": "Critical RCE vulnerability in service X.",
            "affected": "Service X < 2.0",
        },
        "CVE-2024-1234": {
            "cve_id": "CVE-2024-1234",
            "cvss": 7.5,
            "description": "SQL injection in web application Y.",
            "affected": "App Y < 3.1",
        },
    }
    result = cve_db.get(cve_id, {"error": f"Unknown CVE: {cve_id}"})
    return json.dumps(result)


async def _correlate_alerts_callback(ctx: ToolContext, raw_input: str) -> str:
    """``correlate_alerts`` 工具回调 —— Mock 告警关联分析。

    Args:
        ctx: SDK ToolContext。
        raw_input: JSON 字符串，含 ``alerts`` 列表字段。

    Returns:
        JSON 字符串，含关联结果。
    """
    try:
        params = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        params = {}

    alerts = params.get("alerts", [])

    return json.dumps(
        {
            "total_alerts": len(alerts) if isinstance(alerts, list) else 0,
            "correlated_groups": [
                {
                    "group_id": "group-001",
                    "technique": "T1046",
                    "alert_count": len(alerts) if isinstance(alerts, list) else 0,
                    "confidence": 0.92,
                }
            ],
            "false_positives": 0,
        }
    )


# ==================================================================
# JSON Schema 定义
# ==================================================================

_NMAP_SCAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_range": {
            "type": "string",
            "description": "Target network range to scan, e.g. '10.0.0.0/24'",
        }
    },
    "required": ["target_range"],
}

_METASPLOIT_EXPLOIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cve_id": {"type": "string", "description": "CVE identifier, e.g. 'CVE-2024-0001'"},
        "target_host": {"type": "string", "description": "Target host IP address"},
    },
    "required": ["cve_id", "target_host"],
}

_LATERAL_MOVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "from_host": {"type": "string", "description": "Source host IP"},
        "to_host": {"type": "string", "description": "Destination host IP"},
        "technique": {"type": "string", "description": "ATT&CK technique ID, e.g. 'T1021'"},
    },
    "required": ["from_host", "to_host"],
}

_QUERY_ATTCK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "technique_id": {
            "type": "string",
            "description": "ATT&CK technique ID, e.g. 'T1046'",
        }
    },
    "required": ["technique_id"],
}

_QUERY_CVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cve_id": {"type": "string", "description": "CVE identifier, e.g. 'CVE-2024-0001'"}
    },
    "required": ["cve_id"],
}

_CORRELATE_ALERTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "alerts": {
            "type": "array",
            "description": "List of alert objects to correlate",
            "items": {"type": "object"},
        }
    },
    "required": ["alerts"],
}


# ==================================================================
# 工具工厂函数
# ==================================================================


def create_red_team_tools() -> list[Any]:
    """创建红队 SDK FunctionTool 列表。

    红队工具：
        - ``nmap_scan``         — 网络扫描（低风险）
        - ``metasploit_exploit`` — 漏洞利用（高危，needs_approval=True）
        - ``lateral_move_exec``  — 横向移动（高危，needs_approval=True）

    Returns:
        SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
    """
    if not _SDK_FUNCTION_TOOL_AVAILABLE:
        return []

    nmap_tool = FunctionTool(
        name="nmap_scan",
        description="Scan a target network range to discover live hosts, services, and OS info.",
        params_json_schema=_NMAP_SCAN_SCHEMA,
        on_invoke_tool=_nmap_scan_callback,
        needs_approval=False,
    )

    exploit_tool = FunctionTool(
        name="metasploit_exploit",
        description="Execute a Metasploit exploit against a target host for a given CVE.",
        params_json_schema=_METASPLOIT_EXPLOIT_SCHEMA,
        on_invoke_tool=_metasploit_exploit_callback,
        needs_approval=True,  # 高危操作，需审批
    )

    lateral_tool = FunctionTool(
        name="lateral_move_exec",
        description="Execute lateral movement from one host to another using a specified technique.",
        params_json_schema=_LATERAL_MOVE_SCHEMA,
        on_invoke_tool=_lateral_move_exec_callback,
        needs_approval=True,  # 高危操作，需审批
    )

    return [nmap_tool, exploit_tool, lateral_tool]


def create_blue_team_tools() -> list[Any]:
    """创建蓝队 SDK FunctionTool 列表。

    蓝队工具：
        - ``query_attck_kb``    — 查询 ATT&CK 知识库
        - ``query_cve_db``      — 查询 CVE 漏洞库
        - ``correlate_alerts``  — 关联告警分析

    Returns:
        SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
    """
    if not _SDK_FUNCTION_TOOL_AVAILABLE:
        return []

    attck_tool = FunctionTool(
        name="query_attck_kb",
        description="Query the ATT&CK knowledge base for details on a specific technique.",
        params_json_schema=_QUERY_ATTCK_SCHEMA,
        on_invoke_tool=_query_attck_kb_callback,
        needs_approval=False,
    )

    cve_tool = FunctionTool(
        name="query_cve_db",
        description="Query the CVE database for vulnerability details by CVE ID.",
        params_json_schema=_QUERY_CVE_SCHEMA,
        on_invoke_tool=_query_cve_db_callback,
        needs_approval=False,
    )

    correlate_tool = FunctionTool(
        name="correlate_alerts",
        description="Correlate a list of security alerts to identify attack patterns.",
        params_json_schema=_CORRELATE_ALERTS_SCHEMA,
        on_invoke_tool=_correlate_alerts_callback,
        needs_approval=False,
    )

    return [attck_tool, cve_tool, correlate_tool]


def create_all_cyber_tools() -> list[Any]:
    """创建全部攻防 SDK FunctionTool 列表（红队 + 蓝队）。

    Returns:
        SDK ``FunctionTool`` 实例列表。SDK 不可用时返回空列表。
    """
    return create_red_team_tools() + create_blue_team_tools()


# ==================================================================
# 工具名称常量（供编排器引用）
# ==================================================================

RED_TEAM_TOOL_NAMES = {"nmap_scan", "metasploit_exploit", "lateral_move_exec"}
BLUE_TEAM_TOOL_NAMES = {"query_attck_kb", "query_cve_db", "correlate_alerts"}
ALL_TOOL_NAMES = RED_TEAM_TOOL_NAMES | BLUE_TEAM_TOOL_NAMES
