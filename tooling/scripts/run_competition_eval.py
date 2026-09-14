# date: 2026-09-14
# dev: AegisOS
# change: add reproducible competition evidence evaluation for long-horizon drills and heterogeneous routing
"""Run deterministic competition evidence evaluation without external services.

The report measures invariants that can be demonstrated reliably in the mock
runtime: target preservation, round-local event provenance, memory isolation,
checkpoint recovery, tier selection, and node-failure fallback.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Support both ``python -m ...`` and direct execution by file path.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from aegisos_agents.memory.memory_store import MemoryStore
from aegisos_agents.planning.engine.scheduler.scheduler import Model, schedule
from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks.cyber_provider import _CyberMockProvider
from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, Tier
from infrastructure.nodes.dispatcher import ExecutionDispatcher
from infrastructure.nodes.registry import NodeRegistry
from protocol.scheduler import Task


class _EvalNode:
    def __init__(self, profile: NodeProfile, available: bool = True) -> None:
        self.profile = profile
        self.available = available

    def health(self, timeout_s: float = 3.0) -> bool:
        return self.available

    def infer(self, prompt: str, *, system: str = "", **kwargs: object) -> InferenceResult:
        if not self.available:
            return InferenceResult.failure(error="evaluation node unavailable")
        return InferenceResult(
            ok=True,
            text=prompt,
            node_id=self.profile.node_id,
            tier=str(self.profile.tier),
            model_id=self.profile.model_id,
        )


def _long_horizon_case(round_limit: int) -> dict[str, Any]:
    target_range = "10.0.0.0/24"
    drill_id = f"eval-long-{round_limit}"
    memory = MemoryStore()
    started = time.perf_counter()
    result = CyberOrchestrator(mock=_CyberMockProvider()).run_drill(
        target_range,
        max_rounds=round_limit,
        min_rounds=round_limit,
        drill_id=drill_id,
        memory=memory,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    rounds = result["rounds"]
    target_preserved = all(
        target_range in trace["input"]
        for item in rounds
        for trace in item["red"]["agent_trace"]
        if trace["agent"] == "recon"
    )
    event_provenance = all(
        {event["step_id"] for event in item["event_stream"]}
        == {step["step_id"] for step in item["red"]["steps"]}
        and {event["round"] for event in item["event_stream"]} == {item["round"]}
        for item in rounds
    )
    stack = memory.working.get(drill_id)
    memory_isolated = bool(stack) and all(packet.session_id == drill_id for packet in stack)
    checkpoints = memory.checkpoint.list_checkpoints(drill_id)
    restored = memory.checkpoint.restore(drill_id)
    checkpoint_recovered = (
        len(checkpoints) == result["rounds_executed"]
        and restored is not None
        and restored.get("step_index") == result["rounds_executed"]
    )
    return {
        "round_limit": round_limit,
        "rounds_executed": result["rounds_executed"],
        "convergence_code": result["convergence_code"],
        "target_preservation_rate": 1.0 if target_preserved else 0.0,
        "event_provenance_rate": 1.0 if event_provenance else 0.0,
        "memory_isolation_rate": 1.0 if memory_isolated else 0.0,
        "checkpoint_recovery_rate": 1.0 if checkpoint_recovered else 0.0,
        "duration_ms": duration_ms,
        "passed": all((target_preserved, event_provenance, memory_isolated, checkpoint_recovered)),
    }


def _routing_case() -> dict[str, Any]:
    models = [
        Model("device", "device", "small", ["detect"]),
        Model("edge", "edge", "medium", ["detect"]),
        Model("cloud", "cloud", "large", ["detect"]),
    ]
    selected = {
        "local": schedule(Task(goal="local", privacy="local"), models).tier,
        "low_latency": schedule(Task(goal="latency", latency_budget=0.5), models).tier,
        "edge_latency": schedule(Task(goal="latency", latency_budget=3.0), models).tier,
        "heavy": schedule(Task(goal="heavy", latency_budget=60.0), models).tier,
    }
    registry = NodeRegistry()
    device = _EvalNode(
        NodeProfile(node_id="device", tier=Tier.DEVICE, model_id="tiny"),
        available=False,
    )
    edge = _EvalNode(NodeProfile(node_id="edge", tier=Tier.EDGE, model_id="medium"))
    registry.register_node(device)
    registry.register_node(edge)
    registry.tick()
    fallback = ExecutionDispatcher(registry).dispatch(
        Task(goal="private", privacy="local"), "private log"
    )
    passed = selected == {
        "local": "device",
        "low_latency": "device",
        "edge_latency": "edge",
        "heavy": "cloud",
    } and fallback.ok and fallback.tier == "edge"
    return {"selected_tiers": selected, "failure_fallback_tier": fallback.tier, "passed": passed}


def run_evaluation(round_limits: tuple[int, ...] = (5, 10, 20)) -> dict[str, Any]:
    """Run the deterministic evidence suite and return a serializable report."""
    long_horizon = [_long_horizon_case(limit) for limit in round_limits]
    routing = _routing_case()
    passed_cases = sum(item["passed"] for item in long_horizon) + int(routing["passed"])
    total_cases = len(long_horizon) + 1
    return {
        "suite": "XH-202631-evidence-eval",
        "runtime": "mock-deterministic",
        "long_horizon": long_horizon,
        "heterogeneous_routing": routing,
        "passed_cases": passed_cases,
        "total_cases": total_cases,
        "pass_rate": passed_cases / total_cases,
        "limitations": [
            "本报告验证 Mock 编排与不变量，不等同于真实 LLM/真实靶场性能结果。",
            "真实端边云网络和安全工具容器仍需现场环境联调。",
        ],
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# XH-202631 工程证据评测报告",
        "",
        f"运行模式：`{report['runtime']}`",
        f"通过：`{report['passed_cases']}/{report['total_cases']}`（{report['pass_rate']:.0%}）",
        "",
        "## 长程任务保持",
        "",
        "| 轮数上限 | 实际轮数 | 目标保持 | 事件同源 | 记忆隔离 | 检查点恢复 | 耗时 ms |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report["long_horizon"]:
        lines.append(
            f"| {item['round_limit']} | {item['rounds_executed']} | "
            f"{item['target_preservation_rate']:.0%} | {item['event_provenance_rate']:.0%} | "
            f"{item['memory_isolation_rate']:.0%} | {item['checkpoint_recovery_rate']:.0%} | "
            f"{item['duration_ms']:.2f} |"
        )
    routing = report["heterogeneous_routing"]
    lines += ["", "## 动态异构路由", "", f"选择层级：`{routing['selected_tiers']}`", f"设备失效降级：`{routing['failure_fallback_tier']}`", ""]
    lines += ["## 限制", ""] + [f"- {item}" for item in report["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write Markdown report to this path")
    args = parser.parse_args()
    report = run_evaluation()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()