# date: 2026-07-09
# dev: myf
"""R4.5: SDK FunctionTool 攻防工具注册单元测试。

验证：
    - 红队/蓝队/全部工具创建正确
    - 工具 JSON Schema 结构正确
    - 工具回调函数返回正确的 Mock 数据
    - 工具安装到 Agent / 从 Agent 移除
    - 高危工具 needs_approval 属性
    - FunctionTool 不破坏正常编排流程
"""

from __future__ import annotations

import asyncio
import json

import pytest

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from aegisos_agents.tools.cyber_tools import (
    ALL_TOOL_NAMES,
    BLUE_TEAM_TOOL_NAMES,
    RED_TEAM_TOOL_NAMES,
    create_all_cyber_tools,
    create_blue_team_tools,
    create_red_team_tools,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def orch() -> CyberOrchestrator:
    """Mock 模式编排器。"""
    return CyberOrchestrator(mock=MockProvider())


# ------------------------------------------------------------------ #
# 工具创建测试
# ------------------------------------------------------------------ #


class TestToolCreation:
    """测试 FunctionTool 创建。"""

    def test_create_red_team_tools(self):
        """红队工具列表包含 3 个工具。"""
        tools = create_red_team_tools()
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == RED_TEAM_TOOL_NAMES

    def test_create_blue_team_tools(self):
        """蓝队工具列表包含 3 个工具。"""
        tools = create_blue_team_tools()
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == BLUE_TEAM_TOOL_NAMES

    def test_create_all_cyber_tools(self):
        """全部工具列表包含 6 个工具。"""
        tools = create_all_cyber_tools()
        assert len(tools) == 6
        names = {t.name for t in tools}
        assert names == ALL_TOOL_NAMES

    def test_tool_names_constants(self):
        """工具名称常量正确。"""
        assert "nmap_scan" in RED_TEAM_TOOL_NAMES
        assert "metasploit_exploit" in RED_TEAM_TOOL_NAMES
        assert "lateral_move_exec" in RED_TEAM_TOOL_NAMES
        assert "query_attck_kb" in BLUE_TEAM_TOOL_NAMES
        assert "query_cve_db" in BLUE_TEAM_TOOL_NAMES
        assert "correlate_alerts" in BLUE_TEAM_TOOL_NAMES
        assert ALL_TOOL_NAMES == RED_TEAM_TOOL_NAMES | BLUE_TEAM_TOOL_NAMES


# ------------------------------------------------------------------ #
# 工具 Schema 测试
# ------------------------------------------------------------------ #


class TestToolSchemas:
    """测试 FunctionTool 的 JSON Schema。"""

    def test_nmap_scan_schema(self):
        """nmap_scan 的 params_json_schema 正确。"""
        tools = create_red_team_tools()
        nmap = next(t for t in tools if t.name == "nmap_scan")
        schema = nmap.params_json_schema
        assert schema["type"] == "object"
        assert "target_range" in schema["properties"]
        assert "target_range" in schema["required"]

    def test_metasploit_exploit_schema(self):
        """metasploit_exploit 的 params_json_schema 正确。"""
        tools = create_red_team_tools()
        exploit = next(t for t in tools if t.name == "metasploit_exploit")
        schema = exploit.params_json_schema
        assert "cve_id" in schema["properties"]
        assert "target_host" in schema["properties"]
        assert "cve_id" in schema["required"]
        assert "target_host" in schema["required"]

    def test_query_attck_kb_schema(self):
        """query_attck_kb 的 params_json_schema 正确。"""
        tools = create_blue_team_tools()
        attck = next(t for t in tools if t.name == "query_attck_kb")
        schema = attck.params_json_schema
        assert "technique_id" in schema["properties"]
        assert "technique_id" in schema["required"]

    def test_query_cve_db_schema(self):
        """query_cve_db 的 params_json_schema 正确。"""
        tools = create_blue_team_tools()
        cve = next(t for t in tools if t.name == "query_cve_db")
        schema = cve.params_json_schema
        assert "cve_id" in schema["properties"]
        assert "cve_id" in schema["required"]

    def test_correlate_alerts_schema(self):
        """correlate_alerts 的 params_json_schema 正确。"""
        tools = create_blue_team_tools()
        corr = next(t for t in tools if t.name == "correlate_alerts")
        schema = corr.params_json_schema
        assert "alerts" in schema["properties"]
        assert "alerts" in schema["required"]


# ------------------------------------------------------------------ #
# needs_approval 属性测试
# ------------------------------------------------------------------ #


class TestToolApproval:
    """测试 FunctionTool 的 needs_approval 属性。"""

    def test_nmap_scan_no_approval(self):
        """nmap_scan 不需要审批。"""
        tools = create_red_team_tools()
        nmap = next(t for t in tools if t.name == "nmap_scan")
        assert nmap.needs_approval is False

    def test_metasploit_exploit_needs_approval(self):
        """metasploit_exploit 需要审批（高危）。"""
        tools = create_red_team_tools()
        exploit = next(t for t in tools if t.name == "metasploit_exploit")
        assert nmap_approval_true(exploit)

    def test_lateral_move_needs_approval(self):
        """lateral_move_exec 需要审批（高危）。"""
        tools = create_red_team_tools()
        lateral = next(t for t in tools if t.name == "lateral_move_exec")
        assert nmap_approval_true(lateral)

    def test_blue_team_tools_no_approval(self):
        """蓝队工具均不需要审批。"""
        tools = create_blue_team_tools()
        for t in tools:
            assert t.needs_approval is False


def nmap_approval_true(tool) -> bool:
    """检查工具 needs_approval 是否为 True。"""
    return bool(tool.needs_approval)


# ------------------------------------------------------------------ #
# 工具回调测试（Mock 数据）
# ------------------------------------------------------------------ #


class TestToolCallbacks:
    """测试 FunctionTool 回调返回 Mock 数据。"""

    @pytest.mark.asyncio
    async def test_nmap_scan_callback(self):
        """nmap_scan 回调返回资产列表。"""
        tools = create_red_team_tools()
        nmap = next(t for t in tools if t.name == "nmap_scan")
        result = await nmap.on_invoke_tool(None, json.dumps({"target_range": "10.0.0.0/24"}))
        parsed = json.loads(result)
        assert parsed["target_range"] == "10.0.0.0/24"
        assert len(parsed["assets"]) == 2
        assert parsed["assets"][0]["asset_id"] == "asset-001"

    @pytest.mark.asyncio
    async def test_metasploit_exploit_callback(self):
        """metasploit_exploit 回调返回利用结果。"""
        tools = create_red_team_tools()
        exploit = next(t for t in tools if t.name == "metasploit_exploit")
        result = await exploit.on_invoke_tool(
            None, json.dumps({"cve_id": "CVE-2024-0001", "target_host": "10.0.0.5"})
        )
        parsed = json.loads(result)
        assert parsed["cve_id"] == "CVE-2024-0001"
        assert parsed["target_host"] == "10.0.0.5"
        assert parsed["success"] is True

    @pytest.mark.asyncio
    async def test_lateral_move_callback(self):
        """lateral_move_exec 回调返回移动结果。"""
        tools = create_red_team_tools()
        lateral = next(t for t in tools if t.name == "lateral_move_exec")
        result = await lateral.on_invoke_tool(
            None,
            json.dumps(
                {"from_host": "10.0.0.5", "to_host": "10.0.0.10", "technique": "T1021"}
            ),
        )
        parsed = json.loads(result)
        assert parsed["from_host"] == "10.0.0.5"
        assert parsed["to_host"] == "10.0.0.10"
        assert parsed["success"] is True

    @pytest.mark.asyncio
    async def test_query_attck_kb_callback(self):
        """query_attck_kb 回调返回技术详情。"""
        tools = create_blue_team_tools()
        attck = next(t for t in tools if t.name == "query_attck_kb")
        result = await attck.on_invoke_tool(None, json.dumps({"technique_id": "T1046"}))
        parsed = json.loads(result)
        assert parsed["name"] == "Network Service Scanning"
        assert parsed["tactic"] == "Discovery"

    @pytest.mark.asyncio
    async def test_query_cve_db_callback(self):
        """query_cve_db 回调返回 CVE 详情。"""
        tools = create_blue_team_tools()
        cve = next(t for t in tools if t.name == "query_cve_db")
        result = await cve.on_invoke_tool(None, json.dumps({"cve_id": "CVE-2024-0001"}))
        parsed = json.loads(result)
        assert parsed["cve_id"] == "CVE-2024-0001"
        assert parsed["cvss"] == 9.8

    @pytest.mark.asyncio
    async def test_correlate_alerts_callback(self):
        """correlate_alerts 回调返回关联结果。"""
        tools = create_blue_team_tools()
        corr = next(t for t in tools if t.name == "correlate_alerts")
        alerts = [{"alert_id": "a1"}, {"alert_id": "a2"}]
        result = await corr.on_invoke_tool(None, json.dumps({"alerts": alerts}))
        parsed = json.loads(result)
        assert parsed["total_alerts"] == 2
        assert len(parsed["correlated_groups"]) == 1

    @pytest.mark.asyncio
    async def test_callback_handles_invalid_json(self):
        """回调处理无效 JSON 输入不崩溃。"""
        tools = create_red_team_tools()
        nmap = next(t for t in tools if t.name == "nmap_scan")
        result = await nmap.on_invoke_tool(None, "not valid json")
        parsed = json.loads(result)
        assert "assets" in parsed  # 仍有 Mock 数据返回


# ------------------------------------------------------------------ #
# 编排器工具安装测试
# ------------------------------------------------------------------ #


class TestOrchestratorToolInstallation:
    """测试 CyberOrchestrator 的 FunctionTool 安装。"""

    def test_get_red_team_tools(self, orch: CyberOrchestrator):
        """get_red_team_tools 返回 3 个工具。"""
        tools = orch.get_red_team_tools()
        assert len(tools) == 3

    def test_get_blue_team_tools(self, orch: CyberOrchestrator):
        """get_blue_team_tools 返回 3 个工具。"""
        tools = orch.get_blue_team_tools()
        assert len(tools) == 3

    def test_get_all_cyber_tools(self, orch: CyberOrchestrator):
        """get_all_cyber_tools 返回 6 个工具。"""
        tools = orch.get_all_cyber_tools()
        assert len(tools) == 6

    def test_install_red_team_tools(self, orch: CyberOrchestrator):
        """install_red_team_tools 将工具安装到红队 Agent。"""
        tools = orch.install_red_team_tools()
        assert len(tools) == 3

        # recon 有 nmap_scan
        recon_tools = orch.get_agent_tools("recon")
        assert len(recon_tools) == 1
        assert recon_tools[0].name == "nmap_scan"

        # exploit_planner 有 metasploit_exploit + lateral_move_exec
        exploit_tools = orch.get_agent_tools("exploit_planner")
        assert len(exploit_tools) == 2
        names = {t.name for t in exploit_tools}
        assert "metasploit_exploit" in names
        assert "lateral_move_exec" in names

    def test_install_blue_team_tools(self, orch: CyberOrchestrator):
        """install_blue_team_tools 将工具安装到蓝队 Agent。"""
        tools = orch.install_blue_team_tools()
        assert len(tools) == 3

        # detector 有 correlate_alerts + query_attck_kb
        detector_tools = orch.get_agent_tools("detector")
        assert len(detector_tools) == 2

        # triage 有 correlate_alerts
        triage_tools = orch.get_agent_tools("triage")
        assert len(triage_tools) == 1
        assert triage_tools[0].name == "correlate_alerts"

        # vuln_correlator 有 query_cve_db
        vuln_tools = orch.get_agent_tools("vuln_correlator")
        assert len(vuln_tools) == 1
        assert vuln_tools[0].name == "query_cve_db"

        # threat_hunt 有 query_attck_kb
        hunt_tools = orch.get_agent_tools("threat_hunt")
        assert len(hunt_tools) == 1
        assert hunt_tools[0].name == "query_attck_kb"

    def test_install_all_tools(self, orch: CyberOrchestrator):
        """install_all_tools 安装全部 6 个工具。"""
        tools = orch.install_all_tools()
        assert len(tools) == 6

    def test_uninstall_all_tools(self, orch: CyberOrchestrator):
        """uninstall_all_tools 清空所有 Agent 的工具。"""
        orch.install_all_tools()
        orch.uninstall_all_tools()

        agents = [
            "recon",
            "vuln_correlator",
            "exploit_planner",
            "detector",
            "triage",
            "threat_hunt",
            "ir_planner",
            "critic",
            "reviewer",
        ]
        for name in agents:
            assert orch.get_agent_tools(name) == []

    def test_get_agent_tools_invalid_agent(self, orch: CyberOrchestrator):
        """get_agent_tools 对不存在的 Agent 返回空列表。"""
        assert orch.get_agent_tools("nonexistent") == []

    def test_get_high_risk_tools(self, orch: CyberOrchestrator):
        """get_high_risk_tools 返回 2 个高危工具。"""
        tools = orch.get_high_risk_tools()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "metasploit_exploit" in names
        assert "lateral_move_exec" in names

    def test_tools_do_not_break_normal_run(self, orch: CyberOrchestrator):
        """安装工具后编排流程仍正常工作。"""
        orch.install_all_tools()
        result = orch.run_red_chain("10.0.0.0/24")
        assert "chain" in result

        result2 = orch.run_blue_chain([{"type": "scan"}])
        assert "plan" in result2

        # 清理
        orch.uninstall_all_tools()
        # 清理后仍正常
        result3 = orch.run_red_chain("10.0.0.0/24")
        assert "chain" in result3
