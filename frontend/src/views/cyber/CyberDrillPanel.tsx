// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R5 新建 CyberDrillPanel——一键开始/停止 + SSE 轮次时间线 + 收敛总结报告

import { useCallback, useEffect, useRef, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import type {
  DrillEvent,
  DrillRound,
  DrillSummaryResponse,
} from "@/protocol/types";

type DrillPhase = "idle" | "running" | "done" | "aborted" | "error";

/**
 * 多轮攻防演练面板（CyberDrill R5）。
 *
 * 一键「开始演练 → SSE 实时轮次时间线 → 收敛总结报告」，可随时停止。
 * 断线兜底：SSE onError 后改用 getDrill 轮询补拉已发生轮次。
 */
export function CyberDrillPanel() {
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const cyberError = useAppStore((s) => s.cyberError);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const [targetRange, setTargetRange] = useState("10.0.0.0/24");
  const [maxRounds, setMaxRounds] = useState(5);
  const [phase, setPhase] = useState<DrillPhase>("idle");
  const [drillId, setDrillId] = useState<string | null>(null);
  const [rounds, setRounds] = useState<DrillRound[]>([]);
  const [summary, setSummary] = useState<DrillSummaryResponse | null>(null);
  const [expandedRound, setExpandedRound] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reportMd, setReportMd] = useState<string | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);

  const streamCloseRef = useRef<(() => void) | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timelineRef = useRef<HTMLDivElement | null>(null);
  // drillId 的 ref 镜像：SSE onError 回调在 setDrillId 之前的渲染里创建，
  // 闭包拿不到最新 state，必须走 ref 才能触发断线轮询兜底。
  const drillIdRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const handleEvent = useCallback((ev: DrillEvent) => {
    switch (ev.name) {
      case "drill_start":
        setPhase("running");
        setRounds([]);
        setSummary(null);
        setError(null);
        break;
      case "drill_round":
        setRounds((prev) => [...prev, ev.data as DrillRound]);
        break;
      case "drill_summary":
        setSummary(ev.data as DrillSummaryResponse);
        break;
      case "drill_error":
        setError(String(ev.data?.error ?? "Drill failed"));
        setPhase("error");
        break;
      case "drill_done":
        setPhase(ev.data?.error ? "error" : "done");
        streamCloseRef.current?.();
        streamCloseRef.current = null;
        stopPolling();
        break;
      default:
        break;
    }
  }, [stopPolling]);

  /** SSE 断线兜底：改用 getDrill 轮询补拉已发生轮次。 */
  const handleStreamError = useCallback(() => {
    const id = drillIdRef.current;
    if (!id) return;
    stopPolling();
    pollTimerRef.current = setInterval(async () => {
      try {
        const rec = await cyberApi.getDrill(id);
        if (rec.rounds.length > 0) setRounds(rec.rounds);
        if (rec.summary) {
          setSummary(rec.summary);
          setPhase("done");
        }
        if (rec.convergence_code === "aborted") setPhase("aborted");
        if (rec.summary || rec.convergence_code === "aborted") stopPolling();
      } catch {
        /* 网络抖动继续轮询 */
      }
    }, 2000);
  }, [stopPolling]);

  const handleStart = useCallback(async () => {
    setCyberLoading(true);
    setCyberError(null);
    setError(null);
    try {
      const resp = await cyberApi.startDrill({
        target_range: targetRange,
        max_rounds: maxRounds,
      });
      setDrillId(resp.drill_id);
      drillIdRef.current = resp.drill_id;
      setPhase("running");
      setRounds([]);
      setSummary(null);
      streamCloseRef.current = cyberApi.openDrillStream(
        resp.drill_id,
        handleEvent,
        handleStreamError,
      );
    } catch (err) {
      setCyberError(
        err instanceof Error ? err.message : "Failed to start drill",
      );
      setPhase("error");
    } finally {
      setCyberLoading(false);
    }
  }, [targetRange, maxRounds, handleEvent, handleStreamError, setCyberLoading, setCyberError]);

  const handleStop = useCallback(async () => {
    const id = drillIdRef.current;
    if (!id) return;
    try {
      await cyberApi.abortDrill(id);
      // 编排器在下一轮边界中止，SSE 会继续收到 summary/done
    } catch (err) {
      setCyberError(
        err instanceof Error ? err.message : "Failed to abort drill",
      );
    }
  }, [setCyberError]);

  /** 拉取并切换展示运行记录报告（每轮红/蓝/紫产物 + 卸载轨迹 + 收敛总结）。 */
  const handleViewReport = useCallback(async () => {
    const id = drillIdRef.current;
    if (!id) return;
    if (reportMd) {
      setReportOpen((o) => !o);
      return;
    }
    setReportLoading(true);
    try {
      const res = await cyberApi.getDrillReport(id);
      setReportMd(res.report_md);
      setReportOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setReportLoading(false);
    }
  }, [reportMd]);

  // 自动滚动到最新轮次
  useEffect(() => {
    if (timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
    }
  }, [rounds.length]);

  // 卸载清理：关闭 SSE + 停止轮询
  useEffect(() => {
    return () => {
      streamCloseRef.current?.();
      drillIdRef.current = null;
      stopPolling();
    };
  }, [stopPolling]);

  const running = phase === "running";

  return (
    <div className="cyber-panel cyber-drill">
      {/* 控制条 */}
      <div className="cyber-drill__controls">
        <input
          className="cyber-view__range-input"
          type="text"
          value={targetRange}
          onChange={(e) => setTargetRange(e.target.value)}
          placeholder="e.g. 10.0.0.0/24"
          disabled={running || cyberLoading}
          aria-label="Target range"
        />
        <input
          className="cyber-drill__rounds-input"
          type="number"
          min={1}
          max={20}
          value={maxRounds}
          onChange={(e) =>
            setMaxRounds(Math.max(1, Number(e.target.value) || 5))
          }
          disabled={running || cyberLoading}
          aria-label="Max rounds"
          title="Max rounds"
        />
        {running ? (
          <button
            className="cyber-view__btn cyber-view__btn--danger"
            onClick={() => void handleStop()}
          >
            ⏹ Stop
          </button>
        ) : (
          <button
            className="cyber-view__btn cyber-view__btn--primary"
            onClick={() => void handleStart()}
            disabled={cyberLoading}
          >
            {cyberLoading ? "Starting…" : "▶ Start Drill"}
          </button>
        )}
        {drillId ? (
          <span className="cyber-drill__id">
            Drill: <code>{drillId}</code>
            <span
              className={`badge badge--${
                running
                  ? "running"
                  : phase === "done"
                    ? "succeeded"
                    : phase === "error" || phase === "aborted"
                      ? "failed"
                      : "idle"
              }`}
            >
              {phase}
            </span>
          </span>
        ) : null}
      </div>

      {cyberError ? <div className="cyber-view__error">{cyberError}</div> : null}
      {error ? <div className="cyber-drill__error">{error}</div> : null}

      {/* 空态 */}
      {phase === "idle" && !drillId ? (
        <div className="cyber-panel__empty cyber-drill__empty">
          <p className="cyber-panel__hint">
            Run a multi-round red→blue→purple drill with live per-round
            reports. Start to watch the timeline converge.
          </p>
        </div>
      ) : null}

      {/* 轮次时间线 */}
      {rounds.length > 0 || running ? (
        <div className="cyber-drill__timeline" ref={timelineRef}>
          {rounds.map((round) => {
            const isExpanded = expandedRound === round.round;
            return (
              <div
                key={round.round}
                className={`cyber-round${isExpanded ? " cyber-round--expanded" : ""}`}
              >
                <button
                  className="cyber-round__header"
                  onClick={() =>
                    setExpandedRound(isExpanded ? null : round.round)
                  }
                >
                  <span className="cyber-round__num">
                    Round {round.round}
                  </span>
                  <span className="cyber-round__summary">
                    <span className="cyber-round__stat">
                      Red: {round.red.finding_count} findings
                      {round.red.new_steps.length > 0
                        ? ` (+${round.red.new_steps.length} new)`
                        : ""}
                    </span>
                    <span className="cyber-round__stat">
                      Blue: {round.blue.triaged_count} triaged
                    </span>
                    <span className="cyber-round__stat">
                      Purple: {round.purple.new_issue_count} issues
                    </span>
                  </span>
                  {round.prior_rounds_summary ? (
                    <span
                      className="badge badge--info"
                      title={`Prior rounds summary: ${round.prior_rounds_summary}`}
                    >
                      🧠 mem
                    </span>
                  ) : null}
                  {round.phase ? (
                    <span
                      className="cyber-drill__placement"
                      title={`${Object.values(round.phase)
                        .map((p) => `${p.tier} · ${p.reason}`)
                        .join("\n")}`}
                    >
                      {Object.entries(round.phase).map(([phase, p]) => (
                        <span
                          key={phase}
                          className={`badge badge--tier badge--tier-${p.tier}`}
                        >
                          {phase}: {p.tier}
                        </span>
                      ))}
                    </span>
                  ) : null}
                  <span
                    className={`badge badge--${round.purple.converged ? "succeeded" : "running"}`}
                  >
                    {round.purple.converged ? "converged" : "exploring"}
                  </span>
                  <span className="cyber-round__chevron">
                    {isExpanded ? "▾" : "▸"}
                  </span>
                </button>
                {isExpanded ? (
                  <div className="cyber-round__detail">
                    <div className="cyber-panel__grid">
                      <div className="cyber-panel__section">
                        <h5 className="cyber-panel__subtitle">Red</h5>
                        <p className="cyber-panel__text">
                          {round.red.ok
                            ? `Assets: ${round.red.assets.join(", ") || "—"}`
                            : "Red chain failed."}
                        </p>
                        {round.red.new_steps.length > 0 ? (
                          <ul className="cyber-issue-list">
                            {round.red.new_steps.map((step: any, i: number) => (
                              <li key={i} className="cyber-issue">
                                <span className="cyber-issue__icon">+</span>
                                <span>
                                  {step.technique}: {step.from_asset} →{" "}
                                  {step.to_asset}
                                </span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="cyber-panel__empty">No new steps.</p>
                        )}
                      </div>
                      <div className="cyber-panel__section">
                        <h5 className="cyber-panel__subtitle">Blue</h5>
                        <p className="cyber-panel__text">
                          {round.blue.ok
                            ? `Alerts: ${round.blue.alerts.length}`
                            : "Blue chain failed."}
                        </p>
                        {round.blue.plan?.actions ? (
                          <ul className="cyber-issue-list cyber-issue-list--review">
                            {(round.blue.plan.actions as any[]).map(
                              (a: any, i: number) => (
                                <li key={i} className="cyber-issue cyber-issue--review">
                                  <span className="cyber-issue__icon">i</span>
                                  <span>{String(a.action ?? a)}</span>
                                </li>
                              ),
                            )}
                          </ul>
                        ) : (
                          <p className="cyber-panel__empty">No plan actions.</p>
                        )}
                      </div>
                      <div className="cyber-panel__section">
                        <h5 className="cyber-panel__subtitle">Purple</h5>
                        <p className="cyber-panel__text">
                          {round.purple.valid ? "✓ Valid" : "✗ Invalid"} ·{" "}
                          {round.purple.new_issue_count} new issues · code{" "}
                          <code>{round.convergence_code}</code>
                        </p>
                        {round.purple.critique?.suggestion ? (
                          <p className="cyber-panel__text">
                            {round.purple.critique.suggestion}
                          </p>
                        ) : null}
                        {round.purple.review?.overall_assessment ? (
                          <p className="cyber-panel__text">
                            {round.purple.review.overall_assessment}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
          {running ? (
            <div className="cyber-drill__waiting">
              <span className="cyber-drill__spinner" aria-hidden="true" />
              Next round in progress…
            </div>
          ) : null}
        </div>
      ) : null}

      {/* 总结报告 */}
      {summary ? (
        <div className="cyber-drill__summary">
          <h4 className="cyber-panel__subtitle">Drill Summary</h4>
          <div className="cyber-drill__summary-meta">
            <span className={`badge badge--${summary.convergence_code === "converged" ? "succeeded" : "cancelled"}`}>
              {summary.convergence_code}
            </span>
            <span className="cyber-drill__summary-stat">
              {summary.rounds_executed} rounds
            </span>
          </div>
          <p className="cyber-panel__text">{summary.conclusion}</p>
          {summary.memory_trace && summary.memory_trace.length > 0 ? (
            <div className="cyber-drill__memory">
              <h5 className="cyber-drill__memory-title">
                🧠 Cross-Round Memory (跨轮记忆摘要)
              </h5>
              {summary.memory_trace.map((entry) => (
                <div key={entry.stored_task_id} className="cyber-drill__memory-entry">
                  <span className="cyber-drill__memory-round">
                    R{entry.round}
                  </span>
                  <span className="cyber-drill__memory-summary">
                    {entry.next_round_summary ?? entry.packet_summary}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
          {phase === "done" && drillId ? (
            <div className="cyber-drill__report-bar">
              <button
                type="button"
                className="cyber-view__btn"
                onClick={() => void handleViewReport()}
                disabled={reportLoading}
              >
                {reportLoading
                  ? "加载中…"
                  : reportOpen
                    ? "收起运行记录"
                    : "📄 运行记录报告"}
              </button>
              {reportMd ? (
                <span className="cyber-attack__cache-note">
                  每轮红/蓝/紫产物 + 端边云卸载轨迹，Markdown 可复制存档
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* 运行记录报告（折叠展示） */}
      {reportOpen && reportMd ? (
        <pre className="cyber-drill__report">{reportMd}</pre>
      ) : null}
    </div>
  );
}
