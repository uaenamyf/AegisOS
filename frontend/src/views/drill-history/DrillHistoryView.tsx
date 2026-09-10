import { useEffect, useState } from "react";
import { cyberApi } from "@/services/api/cyber";
import type { AgentTraceEntry, DrillMeta, DrillRecord } from "@/protocol/types";

function statusLabel(code: string): string {
  if (code === "converged") return "已收敛";
  if (code === "max_rounds") return "达到轮次上限";
  if (code === "aborted") return "已中止";
  return code || "未知";
}

function statusTone(code: string): string {
  if (code === "converged") return "succeeded";
  if (code === "aborted") return "failed";
  return "pending";
}

function roundTraces(round: DrillRecord["rounds"][number]): AgentTraceEntry[] {
  return [
    ...(round.red.agent_trace ?? []),
    ...(round.blue.agent_trace ?? []),
    ...(round.purple.agent_trace ?? []),
  ];
}

function formatOutput(output: AgentTraceEntry["output"]): string {
  return typeof output === "string" ? output : JSON.stringify(output, null, 2);
}

export function DrillHistoryView() {
  const [drills, setDrills] = useState<DrillMeta[]>([]);
  const [selected, setSelected] = useState<DrillRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [expandedRound, setExpandedRound] = useState<number | null>(null);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await cyberApi.listDrills();
      setDrills(response.drills ?? []);
      if (selected && !response.drills.some((drill) => drill.drill_id === selected.drill_id)) {
        setSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载演练历史");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadHistory();
  }, []);

  const selectDrill = async (drill: DrillMeta) => {
    setDetailLoading(true);
    setError(null);
    try {
      setSelected(await cyberApi.getDrill(drill.drill_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载演练详情");
    } finally {
      setDetailLoading(false);
    }
  };

  const downloadReport = async () => {
    if (!selected || reportLoading) return;
    setReportLoading(true);
    try {
      const report = await cyberApi.getDrillReport(selected.drill_id);
      const blob = new Blob([report.report_md], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${selected.drill_id}.md`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "报告下载失败");
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <section className="view drill-history-view">
      <header className="view__header drill-history__header">
        <div>
          <span className="eyebrow">OPERATIONS / DRILL ARCHIVE</span>
          <h2 className="view__title">演练历史</h2>
          <p className="view__desc">集中回看每次红蓝紫对抗的轮次证据、收敛结论和报告。</p>
        </div>
        <button type="button" className="drill-history__refresh" onClick={() => void loadHistory()} disabled={loading}>
          {loading ? "加载中…" : "↻ 刷新记录"}
        </button>
      </header>

      {error ? <div className="drill-history__error">{error}</div> : null}

      <div className="drill-history__stats" aria-label="演练统计">
        <div><strong>{drills.length}</strong><span>场演练</span></div>
        <div><strong>{drills.reduce((total, drill) => total + drill.rounds_executed, 0)}</strong><span>累计轮次</span></div>
        <div><strong>{drills.filter((drill) => drill.convergence_code === "converged").length}</strong><span>已收敛</span></div>
      </div>

      <div className="drill-history__layout">
        <div className="drill-history__list" aria-label="演练记录列表">
          {loading && drills.length === 0 ? <p className="drill-history__empty">正在读取历史记录…</p> : null}
          {!loading && drills.length === 0 ? <p className="drill-history__empty">暂无演练记录</p> : null}
          {drills.map((drill) => (
            <button
              type="button"
              key={drill.drill_id}
              className={`drill-history__item${selected?.drill_id === drill.drill_id ? " is-selected" : ""}`}
              onClick={() => void selectDrill(drill)}
            >
              <span className="drill-history__item-top">
                <strong>{drill.drill_id}</strong>
                <span className={`badge badge--${statusTone(drill.convergence_code)}`}>{statusLabel(drill.convergence_code)}</span>
              </span>
              <span className="drill-history__item-target">{drill.target_range}</span>
              <span className="drill-history__item-meta">{drill.rounds_executed} 轮 · {drill.created_at?.slice(0, 16).replace("T", " ") || "时间未知"}</span>
            </button>
          ))}
        </div>

        <article className="drill-history__detail" aria-label="演练详情">
          {!selected ? (
            <div className="drill-history__placeholder"><span>↗</span><p>选择一场演练<br />查看红蓝紫协作证据</p></div>
          ) : detailLoading ? (
            <p className="drill-history__empty">正在加载详情…</p>
          ) : (
            <>
              <div className="drill-history__detail-head">
                <div><span className="eyebrow">SELECTED DRILL</span><h3>{selected.drill_id}</h3><p>{selected.target_range}</p></div>
                <button type="button" className="drill-history__report" onClick={() => void downloadReport()} disabled={reportLoading}>{reportLoading ? "导出中…" : "↓ 导出 Markdown"}</button>
              </div>
              <div className="drill-history__summary">
                <div><span>状态</span><strong>{statusLabel(selected.convergence_code)}</strong></div>
                <div><span>执行轮次</span><strong>{selected.rounds_executed} / {selected.max_rounds}</strong></div>
                <div><span>结论</span><strong>{selected.summary?.conclusion || "暂无总结"}</strong></div>
              </div>
              <div className="drill-history__rounds">
                <div className="drill-history__section-title"><span>ROUND EVIDENCE</span><strong>{selected.rounds.length} 轮记录</strong></div>
                {selected.rounds.map((round) => {
                  const traces = roundTraces(round);
                  const expanded = expandedRound === round.round;
                  return <section className={`drill-history__round${expanded ? " is-expanded" : ""}`} key={round.round}>
                    <div className="drill-history__round-marker">R{String(round.round).padStart(2, "0")}</div>
                    <div className="drill-history__round-body">
                      <button type="button" className="drill-history__round-head" onClick={() => setExpandedRound(expanded ? null : round.round)}>
                        <strong>第 {round.round} 轮</strong><span>{round.convergence_code} · {traces.length} 个 Agent</span>
                      </button>
                      <div className="drill-history__teams">
                        <div className="team-pill team-pill--red"><b>红队</b><span>{round.red.finding_count} findings · +{round.red.new_steps.length} steps</span></div>
                        <div className="team-pill team-pill--blue"><b>蓝队</b><span>{round.blue.triaged_count} triaged · {round.blue.plan?.actions?.length ?? 0} actions</span></div>
                        <div className="team-pill team-pill--purple"><b>紫队</b><span>{round.purple.valid ? "链路通过" : `${round.purple.new_issue_count} 个缺口`}</span></div>
                      </div>
                      {expanded ? <div className="drill-history__traces">
                        <div className="drill-history__trace-title">AGENT TRACE <span>按执行顺序展开输入与输出</span></div>
                        {traces.length ? traces.map((trace, index) => (
                          <article className="agent-trace" key={`${trace.agent}-${index}`}>
                            <header><strong>{trace.agent}</strong><span>STEP {String(index + 1).padStart(2, "0")}</span></header>
                            <div><label>输入</label><pre>{trace.input}</pre></div>
                            <div><label>输出</label><pre>{formatOutput(trace.output)}</pre></div>
                          </article>
                        )) : <p className="drill-history__empty">本轮没有逐 Agent trace。</p>}
                      </div> : null}
                    </div>
                  </section>;
                })}
              </div>
            </>
          )}
        </article>
      </div>
    </section>
  );
}