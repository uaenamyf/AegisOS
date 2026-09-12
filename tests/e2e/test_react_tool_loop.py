# @aegis-gen
# date: 2026-08-12
# dev: Codex
# change: AP2.7 验证五个 Agent 的 ReAct 工具调用循环与可审计轨迹
"""AP2.7 ReAct 工具调用循环端到端测试。"""

from __future__ import annotations

from aegisos_agents.action.detector.agent import DetectorAgent
from aegisos_agents.action.forensics.agent import ForensicsAgent
from aegisos_agents.action.recon.agent import ReconAgent
from aegisos_agents.action.threat_hunt.agent import ThreatHuntAgent
from aegisos_agents.action.vuln_correlator.agent import VulnCorrelatorAgent
from aegisos_agents.perception.reasoning.strategies import ReactStatus
from aegisos_agents.tools.llms.base import LLMRequest, LLMResponse
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import DefenseAction, ResponsePlan
from protocol.tool import ToolCall, ToolResult


class _ScenarioExecutor:
    """按工具名返回确定性观察，并记录完整调用顺序。"""

    def __init__(self) -> None:
        self.calls: list[ToolCall] = []
        self.outputs: dict[str, dict[str, object]] = {
            "nmap_scan": {
                "observation_id": "obs-recon",
                "hosts": [{"host": "10.0.0.8", "ports": [22]}],
            },
            "query_cve_db": {
                "observation_id": "obs-vuln",
                "matches": [{"asset_id": "asset-1", "cve_id": "CVE-2026-0001"}],
            },
            "correlate_alerts": {
                "observation_id": "obs-detector",
                "groups": [{"asset_id": "asset-1", "technique": "T1110"}],
            },
            "query_attck_kb": {
                "observation_id": "obs-hunt",
                "technique_id": "T1110",
                "name": "Brute Force",
            },
            "collect_forensic_evidence": {
                "observation_id": "obs-forensics",
                "artifacts": ["auth.log"],
            },
        }

    def execute(self, call: ToolCall) -> ToolResult:
        """执行已注册的场景工具，并关联请求与观察的 call_id。"""
        self.calls.append(call)
        return ToolResult(
            call_id=call.call_id,
            ok=True,
            output=self.outputs[call.name],
            meta={"executor": "ap2.7-scenario"},
        )


class _RecordingProvider(MockProvider):  # type: ignore[misc]
    """记录最终归纳 prompt，证明工具观察进入 finish 阶段。"""

    def __init__(self, response: str) -> None:
        super().__init__({"default": response})
        self.prompts: list[str] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        """记录请求后返回预置结构化响应。"""
        self.prompts.append(request.prompt)
        return super().complete(request)


def test_five_agents_complete_react_tool_loops_with_auditable_traces() -> None:
    """五个 Agent 应依次完成 think→act→observe→finish 并保留调用轨迹。"""
    executor = _ScenarioExecutor()
    providers = [
        _RecordingProvider(
            '{"assets":[{"asset_id":"asset-1","host":"10.0.0.8",'
            '"services":["ssh:22"],"os":"linux","exposure":"external"}]}'
        ),
        _RecordingProvider(
            '{"findings":[{"finding_id":"finding-1","cve_id":"CVE-2026-0001",'
            '"asset_id":"asset-1","cvss":9.1,"attack_surface":"ssh"}]}'
        ),
        _RecordingProvider(
            '{"alerts":[{"alert_id":"alert-1","severity":"high","src":"internet",'
            '"dst":"asset-1","technique":"T1110","raw":{"attempts":42}}]}'
        ),
        _RecordingProvider(
            '{"hypotheses":[{"hypothesis":"credential brute force",'
            '"confidence":0.92,"technique":"T1110"}]}'
        ),
        _RecordingProvider(
            '{"report_id":"report-1","root_cause":"weak password",'
            '"timeline":[{"ts":"2026-08-12T00:00:00Z","event":"login attempts"}],'
            '"recommendations":["rotate credentials"]}'
        ),
    ]

    recon_result = ReconAgent(provider=providers[0]).scan_react("10.0.0.0/24", executor)
    assert recon_result.final_output is not None

    vuln_result = VulnCorrelatorAgent(provider=providers[1]).correlate_react(
        recon_result.final_output,
        executor,
    )
    assert vuln_result.final_output is not None
    events = [
        {
            "type": "vulnerability_probe",
            "asset_id": finding.asset_id,
            "cve_id": finding.cve_id,
        }
        for finding in vuln_result.final_output
    ]

    detector_result = DetectorAgent(provider=providers[2]).detect_react(events, executor)
    assert detector_result.final_output is not None

    hunt_result = ThreatHuntAgent(provider=providers[3]).hunt_react(
        detector_result.final_output,
        executor,
    )
    assert hunt_result.final_output is not None

    response_plan = ResponsePlan(
        plan_id="plan-1",
        actions=[
            DefenseAction(
                action_id="isolate-1",
                kind="isolate",
                target=detector_result.final_output[0].dst,
                rationale=hunt_result.final_output[0]["hypothesis"],
            )
        ],
        confidence=hunt_result.final_output[0]["confidence"],
    )
    forensics_result = ForensicsAgent(provider=providers[4]).investigate_react(
        response_plan,
        executor,
    )

    results = [
        recon_result,
        vuln_result,
        detector_result,
        hunt_result,
        forensics_result,
    ]
    expected_tools = [
        "nmap_scan",
        "query_cve_db",
        "correlate_alerts",
        "query_attck_kb",
        "collect_forensic_evidence",
    ]
    expected_permissions = [
        "network.scan",
        "knowledge.read",
        "telemetry.read",
        "knowledge.read",
        "evidence.read",
    ]

    assert [call.name for call in executor.calls] == expected_tools
    assert [call.permission for call in executor.calls] == expected_permissions
    for result, call in zip(results, executor.calls, strict=True):
        assert result.status is ReactStatus.Succeeded
        assert result.succeeded is True
        assert len(result.steps) == 1
        step = result.steps[0]
        assert step.iteration == 1
        assert step.action is call
        assert step.observation.ok is True
        assert step.observation.call_id == call.call_id
        assert step.observation.meta["executor"] == "ap2.7-scenario"
        assert result.final_thought

    for provider, tool_name in zip(providers, expected_tools, strict=True):
        assert len(provider.prompts) == 1
        assert "UNTRUSTED_TOOL_OUTPUT_JSON" in provider.prompts[0]
        observation_id = executor.outputs[tool_name]["observation_id"]
        assert isinstance(observation_id, str)
        assert observation_id in provider.prompts[0]

    assert vuln_result.final_output[0].asset_id == recon_result.final_output[0].asset_id
    assert detector_result.final_output[0].dst == vuln_result.final_output[0].asset_id
    assert hunt_result.final_output[0]["technique"] == detector_result.final_output[0].technique
    assert forensics_result.final_output is not None
    assert forensics_result.final_output["report_id"] == "report-1"
