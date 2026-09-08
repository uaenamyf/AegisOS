# date: 2026-09-05
# dev: OpenSquilla
# changelog: 新建——Auto Drill 运行记录报告生成器（每轮红/蓝/紫产物 + 卸载位置 + 收敛总结）
"""Auto Drill 运行记录报告生成器。

把一次完整演练的产物渲染为结构化 Markdown 报告并落盘：
    - 头部元信息（drill_id / 目标 / 轮次 / 收敛码 / 模式相关说明）
    - 每轮红（资产/漏洞/攻击步骤）/ 蓝（告警/分诊/响应动作）/ 紫（评审/建议/有效性）
    - 端-边-云卸载位置随轮次变化（自适应调度轨迹）
    - 跨轮记忆摘要与收敛总结

落盘位置：``data/drills/reports/<drill_id>.md``（与 JSON 原始记录并存，供复盘与解读）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "drills" / "reports"

_PHASE_LABELS = {"red": "红队攻击", "blue": "蓝队防御", "purple": "紫队评审"}


def _fmt_step(step: dict[str, Any]) -> str:
    """格式化一个攻击步骤。"""
    from_ = step.get("from_asset", "?")
    to_ = step.get("to_asset", "?")
    ok = "✓" if step.get("success") else "✗"
    return f"- `{ok}` {step.get('technique', '?')}（{from_} → {to_}）"


def _fmt_alert(alert: dict[str, Any]) -> str:
    """格式化一条告警。"""
    sev = str(alert.get("severity", "low")).upper()
    return (
        f"- [{sev}] {alert.get('alert_id', '?')}: "
        f"{alert.get('src', '?')} → {alert.get('dst', '?')} · {alert.get('technique', '?')}"
    )


def _fmt_action(action: dict[str, Any]) -> str:
    """格式化一个响应动作。"""
    return f"- {action.get('action', action)}"


def _compact(text: Any, limit: int = 500) -> str:
    """截断长文本，保留可读性并标注总长度。"""
    s = str(text)
    if len(s) <= limit:
        return s
    return f"{s[:limit]}…（截断，共 {len(s)} 字符）"


def _fmt_agent_trace(trace: list[dict[str, Any]]) -> str:
    """格式化 agent 级调用追踪（每个 agent 的输入 prompt 与结构化输出）。"""
    if not trace:
        return "- 无 agent 调用记录。"
    lines: list[str] = []
    for t in trace:
        agent = t.get("agent", "?")
        inp = _compact(t.get("input", ""))
        out = _compact(json.dumps(t.get("output", {}), ensure_ascii=False, default=str))
        lines.append(f"- **{agent}**")
        lines.append(f"  - 输入: `{inp}`")
        lines.append(f"  - 输出: `{out}`")
    return "\n".join(lines)


def _fmt_phase_table(phases: dict[str, dict[str, Any]]) -> str:
    """渲染端-边-云卸载位置表格。"""
    rows = ["| 阶段 | 执行层 | 理由 |", "|---|---|---|"]
    for phase in ("red", "blue", "purple"):
        p = phases.get(phase, {})
        rows.append(
            f"| {_PHASE_LABELS.get(phase, phase)} | `{p.get('tier', '?')}` "
            f"({p.get('model_id', '?')}) | {p.get('reason', '?')} |"
        )
    return "\n".join(rows)


def build_drill_report(record: dict[str, Any]) -> str:
    """把演练记录渲染为 Markdown 报告。

    Args:
        record: ``CyberDefenseService.drill`` 返回的完整记录（含 rounds/summary）。

    Returns:
        Markdown 报告文本。
    """
    lines: list[str] = []
    drill_id = record.get("drill_id", "?")
    rounds = record.get("rounds", [])
    summary = record.get("summary") or {}

    lines.append(f"# Auto Drill 运行记录 — {drill_id}")
    lines.append("")
    lines.append("> 本报告由后端在演练结束时自动生成，完整原始数据见 "
                 "`data/drills/<drill_id>.json`（前端展示与 SSE 推送同源）。")
    lines.append("")

    # ---- 元信息 ----
    lines.append("## 1. 演练元信息")
    lines.append("")
    lines.append("| 字段 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 演练 ID | `{drill_id}` |")
    lines.append(f"| 目标网络 | `{record.get('target_range', '?')}` |")
    lines.append(f"| 轮次上限 | {record.get('max_rounds', '?')} |")
    lines.append(f"| 实际轮次 | {record.get('rounds_executed', len(rounds))} |")
    lines.append(f"| 收敛码 | `{record.get('convergence_code', '?')}` |")
    if summary.get("conclusion"):
        lines.append(f"| 结论 | {summary.get('conclusion')} |")
    lines.append("")

    # ---- 卸载位置总览 ----
    lines.append("## 2. 端-边-云卸载轨迹（自适应调度）")
    lines.append("")
    lines.append("> 卸载位置随轮次与收敛负载自适应变化；真实 LLM 模式下端/边暂未接独立 "
                 "API，统一降级云侧执行（理由中注明）。")
    lines.append("")
    for r in rounds:
        phase = r.get("phase")
        if not phase:
            continue
        lines.append(f"### 第 {r.get('round', '?')} 轮")
        lines.append("")
        lines.append(_fmt_phase_table(phase))
        lines.append("")

    # ---- 逐轮战报 ----
    lines.append("## 3. 逐轮战报")
    lines.append("")
    for r in rounds:
        rn = r.get("round", "?")
        red = r.get("red", {})
        blue = r.get("blue", {})
        purple = r.get("purple", {})
        lines.append(f"## Round {rn}（收敛码 `{r.get('convergence_code', '?')}`）")
        lines.append("")

        # 红队
        lines.append("### 🟥 红队攻击")
        lines.append("")
        if red.get("ok"):
            assets = red.get("assets") or []
            lines.append(f"- 发现资产：{len(assets)} 台（{', '.join(assets) if assets else '—'}）")
            lines.append(f"- 漏洞条目：{red.get('finding_count', 0)} 条")
            new_steps = red.get("new_steps") or []
            steps = red.get("steps") or []
            if new_steps:
                lines.append(f"- **本轮新增攻击步骤（{len(new_steps)}）**：")
                lines.append("")
                lines.extend(_fmt_step(s) for s in new_steps)
                lines.append("")
            if steps:
                lines.append(f"- 累计攻击链（{len(steps)} 步）：")
                lines.append("")
                lines.extend(_fmt_step(s) for s in steps)
                lines.append("")
        else:
            lines.append("- 红队链执行失败。")
        lines.append("")
        lines.append("#### 🔍 Agent 调用追踪（红队）")
        lines.append("")
        lines.append(_fmt_agent_trace(red.get("agent_trace") or []))
        lines.append("")

        # 蓝队
        lines.append("### 🟦 蓝队防御")
        lines.append("")
        if blue.get("ok"):
            alerts = blue.get("alerts") or []
            lines.append(f"- 检出告警：{len(alerts)} 条")
            lines.append(f"- 分诊归类：{blue.get('triaged_count', 0)} 条")
            if alerts:
                lines.append("")
                lines.extend(_fmt_alert(a) for a in alerts)
                lines.append("")
            plan = blue.get("plan") or {}
            actions = plan.get("actions") or []
            if actions:
                lines.append(f"- 响应计划（置信度 {plan.get('confidence', '?')}）：")
                lines.append("")
                lines.extend(_fmt_action(a) for a in actions)
                lines.append("")
            else:
                lines.append("- 响应计划：无动作（可能因事件流无新增告警）。")
        else:
            lines.append(f"- 蓝队链执行失败：{blue.get('error', 'unknown')}")
        lines.append("")
        lines.append("#### 🔍 Agent 调用追踪（蓝队）")
        lines.append("")
        lines.append(_fmt_agent_trace(blue.get("agent_trace") or []))
        lines.append("")

        # 紫队
        lines.append("### 🟪 紫队评审")
        lines.append("")
        if purple.get("ok"):
            critique = purple.get("critique") or {}
            review = purple.get("review") or {}
            issues = critique.get("issues") or []
            lines.append(
                f"- 一致性校验：{'✓ 通过' if purple.get('valid') else '✗ 未通过'} · "
                f"新发现问题 {purple.get('new_issue_count', len(issues))} 条 · "
                f"收敛：{'是' if purple.get('converged') else '否'}"
            )
            if issues:
                lines.append("")
                for issue in issues:
                    lines.append(f"- ⚠ {issue}")
                lines.append("")
            if critique.get("suggestion"):
                lines.append(f"- 建议：{critique.get('suggestion')}")
            if review.get("overall_assessment"):
                lines.append(f"- 总评：{review.get('overall_assessment')}")
        else:
            lines.append("- 紫队链执行失败。")
        lines.append("")
        lines.append("#### 🔍 Agent 调用追踪（紫队）")
        lines.append("")
        lines.append(_fmt_agent_trace(purple.get("agent_trace") or []))
        lines.append("")

        # 跨轮记忆
        if r.get("prior_rounds_summary"):
            lines.append("#### 🧠 携带的跨轮记忆摘要")
            lines.append("")
            lines.append(f"```\n{r.get('prior_rounds_summary')}\n```")
            lines.append("")

    # ---- 总结 ----
    lines.append("## 4. 收敛总结")
    lines.append("")
    lines.append(f"- 收敛码：`{record.get('convergence_code', '?')}`")
    lines.append(f"- 实际轮次：{record.get('rounds_executed', len(rounds))}")
    lines.append(f"- 结论：{summary.get('conclusion', '—')}")
    memory_trace = summary.get("memory_trace") or []
    if memory_trace:
        lines.append("")
        lines.append("### 🧠 跨轮记忆轨迹")
        lines.append("")
        for entry in memory_trace:
            lines.append(
                f"- R{entry.get('round', '?')} `{entry.get('stored_task_id', '?')}`："
                f"{entry.get('next_round_summary') or entry.get('packet_summary', '')}"
            )
    lines.append("")
    lines.append("---")
    lines.append("*记录由 AegisOS Auto Drill 运行记录生成器自动生成。*")
    lines.append("")
    return "\n".join(lines)


def write_drill_report(record: dict[str, Any], out_dir: Path | None = None) -> Path:
    """把演练记录报告落盘。

    Args:
        record: 演练记录。
        out_dir: 输出目录；None 时用默认 ``data/drills/reports``。

    Returns:
        写出的报告文件路径。
    """
    target = out_dir or _REPORTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{record.get('drill_id', 'drill_unknown')}.md"
    path.write_text(build_drill_report(record), encoding="utf-8")
    return path


def build_drill_report_json(record: dict[str, Any]) -> dict[str, Any]:
    """供 ``GET /drill/{id}/report`` 返回的 JSON 载荷。"""
    return {
        "drill_id": record.get("drill_id"),
        "report_md": build_drill_report(record),
        "rounds_executed": record.get("rounds_executed"),
        "convergence_code": record.get("convergence_code"),
        "raw_json_path": f"data/drills/{record.get('drill_id')}.json",
    }
