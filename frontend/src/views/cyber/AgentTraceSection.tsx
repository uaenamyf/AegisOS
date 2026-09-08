// date: 2026-09-06
// dev: AegisOS Dev
// changelog: R15 新建 AgentTraceSection——通用「逐 agent 输入输出」追踪组件
//   红/蓝/紫单链面板与 Auto Drill 轮次详情复用；可折叠、JSON 可展开

import { useState } from "react";
import type { AgentTraceEntry } from "@/protocol/types";

const AGENT_LABELS: Record<string, string> = {
  // 红队
  recon: "侦察 Recon",
  vuln_correlator: "漏洞关联 Vuln Correlator",
  exploit_planner: "攻击链规划 Exploit Planner",
  // 蓝队
  detector: "入侵检测 Detector",
  triage: "告警分诊 Triage",
  threat_hunt: "威胁狩猎 Threat Hunt",
  ir_planner: "响应规划 IR Planner",
  // 紫队
  critic: "攻击链批判 Critic",
  reviewer: "一致性审查 Reviewer",
};

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function summarizeOutput(output: unknown): string {
  if (output == null) return "∅";
  if (typeof output === "string") return output.length > 160 ? output.slice(0, 160) + "…" : output;
  try {
    const s = JSON.stringify(output);
    return s.length > 160 ? s.slice(0, 160) + "…" : s;
  } catch {
    return String(output);
  }
}

/**
 * 逐 agent 输入输出追踪区（R15 可观测性）。
 *
 * 每个 agent 条目可独立展开：默认显示 agent 名 + 输入摘要 + 输出摘要，
 * 展开后展示完整输入 prompt 与结构化输出 JSON。
 */
export function AgentTraceSection({
  trace,
  title = "Agent 运行记录",
}: {
  trace?: AgentTraceEntry[] | null;
  title?: string;
}) {
  const [open, setOpen] = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (!trace || trace.length === 0) return null;

  return (
    <div className="cyber-trace">
      <button
        className="cyber-trace__header"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="cyber-trace__toggle">{open ? "▼" : "▶"}</span>
        <span>{title}</span>
        <span className="cyber-trace__count">{trace.length} agents</span>
      </button>

      {open ? (
        <div className="cyber-trace__body">
          {trace.map((entry, i) => {
            const label = AGENT_LABELS[entry.agent] ?? entry.agent;
            const expanded = expandedIdx === i;
            return (
              <div key={`${entry.agent}-${i}`} className="cyber-trace__entry">
                <button
                  className="cyber-trace__entry-header"
                  onClick={() => setExpandedIdx(expanded ? null : i)}
                  aria-expanded={expanded}
                >
                  <span className="cyber-trace__step">{i + 1}</span>
                  <span className="cyber-trace__agent">{label}</span>
                  <span className="cyber-trace__summary">{summarizeOutput(entry.output)}</span>
                </button>
                {expanded ? (
                  <div className="cyber-trace__detail">
                    <div className="cyber-trace__block">
                      <span className="cyber-trace__block-label">输入 Input</span>
                      <pre className="cyber-trace__pre">{entry.input}</pre>
                    </div>
                    <div className="cyber-trace__block">
                      <span className="cyber-trace__block-label">输出 Output</span>
                      <pre className="cyber-trace__pre">{prettyJson(entry.output)}</pre>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
