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

// T3 收敛趋势图：每轮指标计算
// 防御覆盖率复用 T6 算法：该轮红队新增步骤技法 ∩ 蓝队告警技法 / 红队技法
function roundCoverage(round: DrillRound): number | null {
  const attackTechs = [
    ...new Set(
      (round.red.new_steps ?? [])
        .map((s: any) => s.technique)
        .filter(Boolean),
    ),
  ];
  const detectTechs = [
    ...new Set(
      (round.blue.alerts ?? [])
        .map((a: any) => a.technique)
        .filter(Boolean),
    ),
  ];
  if (attackTechs.length === 0) return null;
  const covered = attackTechs.filter((t) => detectTechs.includes(t)).length;
  return Math.round((covered / attackTechs.length) * 100);
}

/** T3 收敛趋势图：SVG 多折线（红队新增步骤/蓝队动作/覆盖率 + 紫队判定 + 收敛标注）。 */
function TrendChart({ rounds }: { rounds: DrillRound[] }) {
  const W = 560;
  const H = 178;
  const PAD_L = 36;
  const PAD_R = 46;
  const PAD_T = 20;
  const PAD_B = 26;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  const n = rounds.length;

  const series = rounds.map((r) => ({
    round: r.round,
    red: (r.red.new_steps ?? []).length,
    blue: (r.blue.plan?.actions?.length ?? 0),
    cov: roundCoverage(r),
    valid: r.purple?.valid,
  }));

  const maxVal = Math.max(
    1,
    ...series.map((s) => Math.max(s.red, s.blue)),
  );
  const x = (i: number) =>
    PAD_L + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
  const y = (v: number, max: number) =>
    PAD_T + plotH - (v / max) * plotH;
  const line = (key: "red" | "blue") =>
    series
      .map((s, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(s[key], maxVal)}`)
      .join(" ");
  // 覆盖率单独缩放到 0-100
  const covLine = series
    .map((s, i) => {
      const v = s.cov ?? 0;
      return `${i === 0 ? "M" : "L"} ${x(i)} ${y(v, 100)}`;
    })
    .join(" ");

  const lastRound = rounds[rounds.length - 1];

  return (
    <div className="cyber-trend">
      <div className="cyber-trend__head">
        <h5 className="cyber-panel__subtitle">
          📈 收敛趋势 · 证据驱动对抗
        </h5>
        <div className="cyber-trend__legend">
          <span><i className="cyber-trend__ln--red" />红队新增步骤</span>
          <span><i className="cyber-trend__ln--blue" />蓝队动作</span>
          <span><i className="cyber-trend__ln--green" />防御覆盖率 %</span>
          <span>● 紫队判定 ✓/✗</span>
        </div>
      </div>
      <svg className="cyber-trend__svg" viewBox={`0 0 ${W} ${H}`}>
        {/* 网格线 */}
        {[0, 0.5, 1].map((t) => (
          <line
            key={t}
            x1={PAD_L}
            x2={W - PAD_R}
            y1={PAD_T + plotH * (1 - t)}
            y2={PAD_T + plotH * (1 - t)}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="1"
          />
        ))}
        {/* X 轴 */}
        <line
          x1={PAD_L}
          x2={W - PAD_R}
          y1={PAD_T + plotH}
          y2={PAD_T + plotH}
          stroke="rgba(255,255,255,0.25)"
          strokeWidth="1"
        />
        {series.map((s, i) => (
          <text
            key={`x${i}`}
            x={x(i)}
            y={H - 8}
            fill="var(--text-secondary)"
            fontSize="10"
            textAnchor="middle"
          >
            R{s.round}
          </text>
        ))}
        {/* 收敛标注：最后一轮高亮竖线 */}
        <line
          x1={x(n - 1)}
          x2={x(n - 1)}
          y1={PAD_T - 4}
          y2={PAD_T + plotH}
          stroke="#d9a13b"
          strokeWidth="1.5"
          strokeDasharray="4 3"
        />
        <text
          x={x(n - 1)}
          y={PAD_T - 8}
          fill="#d9a13b"
          fontSize="11"
          fontWeight="600"
          textAnchor="middle"
        >
          ⚑ 收敛
        </text>
        {/* 三条趋势线 */}
        <path d={line("red")} fill="none" stroke="#e05252" strokeWidth="2" />
        <path d={line("blue")} fill="none" stroke="#2f7de1" strokeWidth="2" />
        <path d={covLine} fill="none" stroke="#2e9e5b" strokeWidth="2" />
        {/* 数据点 + 紫队判定 */}
        {series.map((s, i) => (
          <g key={`p${i}`}>
            <circle cx={x(i)} cy={y(s.red, maxVal)} r="3" fill="#e05252" />
            <circle cx={x(i)} cy={y(s.blue, maxVal)} r="3" fill="#2f7de1" />
            {s.cov != null && (
              <circle cx={x(i)} cy={y(s.cov, 100)} r="3" fill="#2e9e5b" />
            )}
            <text
              x={x(i)}
              y={PAD_T - 2}
              fill={s.valid ? "#2e9e5b" : "#e05252"}
              fontSize="12"
              fontWeight="700"
              textAnchor="middle"
            >
              {s.valid ? "✓" : "✗"}
            </text>
            <text
              x={x(i)}
              y={y(s.red, maxVal) - 6}
              fill="var(--text-secondary)"
              fontSize="9"
              textAnchor="middle"
            >
              {s.red}
            </text>
            <text
              x={x(i)}
              y={y(s.blue, maxVal) + 11}
              fill="var(--text-secondary)"
              fontSize="9"
              textAnchor="middle"
            >
              {s.blue}
            </text>
            {s.cov != null && (
              <text
                x={x(i)}
                y={y(s.cov, 100) - 6}
                fill="var(--text-secondary)"
                fontSize="9"
                textAnchor="middle"
              >
                {s.cov}%
              </text>
            )}
          </g>
        ))}
        {/* 轮次标签轴说明 */}
        <text
          x={W - PAD_R}
          y={PAD_T + plotH + 16}
          fill="var(--text-dim)"
          fontSize="9"
          textAnchor="end"
        >
          round
        </text>
      </svg>
      <p className="cyber-trend__note">
        {lastRound.convergence_code === "max_rounds"
          ? `已达最大轮次上限收敛（${lastRound.convergence_code}）`
          : `证据驱动收敛（${lastRound.convergence_code ?? "converged"}）：紫队反馈驱动红队演化，缺口逐步闭合`}
      </p>
    </div>
  );
}

/** 最近一轮演练的浏览器快照（sessionStorage）：切 tab/刷新后仍可恢复展示，
 *  只有开启新一轮时才被清除/覆盖。 */
const DRILL_SNAPSHOT_KEY = "aegis.cyber-drill.snapshot";

// R10 端-边-云执行位置展示（T4）
// 层级语义与后端调度器一致：端侧超低延迟/本地隐私 / 边侧低延迟/区域隔离 / 云侧强算力/可脱敏
const TIER_META: Record<string, { label: string; cls: string; icon: string }> = {
  device: { label: "端侧", cls: "device", icon: "▣" },
  edge: { label: "边侧", cls: "edge", icon: "◈" },
  cloud: { label: "云侧", cls: "cloud", icon: "☁" },
};

const PHASE_META: Record<string, { label: string; desc: string }> = {
  red: { label: "红队攻击", desc: "侦察 → 漏洞 → 攻击链" },
  blue: { label: "蓝队防御", desc: "检测 → 分诊 → 狩猎 → 响应" },
  purple: { label: "紫队评审", desc: "批判 + 一致性审查" },
};

interface DrillSnapshot {
  drillId: string | null;
  phase: DrillPhase;
  rounds: DrillRound[];
  summary: DrillSummaryResponse | null;
  reportMd: string | null;
}

function loadSnapshot(): DrillSnapshot | null {
  try {
    const raw = sessionStorage.getItem(DRILL_SNAPSHOT_KEY);
    return raw ? (JSON.parse(raw) as DrillSnapshot) : null;
  } catch {
    return null;
  }
}

function saveSnapshot(snap: DrillSnapshot): void {
  try {
    sessionStorage.setItem(DRILL_SNAPSHOT_KEY, JSON.stringify(snap));
  } catch {
    /* 存储不可用（隐私模式等）时静默降级，仅影响跨页恢复 */
  }
}

function clearSnapshot(): void {
  try {
    sessionStorage.removeItem(DRILL_SNAPSHOT_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * 多轮攻防演练面板（CyberDrill R5）。
 *
 * 一键「开始演练 → SSE 实时轮次时间线 → 收敛总结报告」，可随时停止。
 * 断线兜底：SSE onError 后改用 getDrill 轮询补拉已发生轮次。
 * 结果持久化：最近一轮结果存 sessionStorage，切换页面/刷新后恢复展示，
 * 开启新一轮时才清除旧结果。
 */
export function CyberDrillPanel() {
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const cyberError = useAppStore((s) => s.cyberError);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  // 首次渲染读一次快照，之后组件生命周期内不再变化（开新轮才覆盖）
  const initialSnapshotRef = useRef<DrillSnapshot | null>(null);
  if (initialSnapshotRef.current === null) {
    initialSnapshotRef.current = loadSnapshot();
  }
  const initialSnapshot = initialSnapshotRef.current;

  const [targetRange, setTargetRange] = useState("10.0.0.0/24");
  const [maxRounds, setMaxRounds] = useState(5);
  const [phase, setPhase] = useState<DrillPhase>(() => {
    if (!initialSnapshot) return "idle";
    // 旧会话遗留的 running 无意义（SSE 已断）：有 summary 视为已完成，
    // 否则视为被中断
    if (initialSnapshot.phase === "running") {
      return initialSnapshot.summary ? "done" : "aborted";
    }
    return initialSnapshot.phase;
  });
  const [drillId, setDrillId] = useState<string | null>(
    initialSnapshot?.drillId ?? null,
  );
  const [rounds, setRounds] = useState<DrillRound[]>(
    initialSnapshot?.rounds ?? [],
  );
  const [summary, setSummary] = useState<DrillSummaryResponse | null>(
    initialSnapshot?.summary ?? null,
  );
  const [expandedRound, setExpandedRound] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reportMd, setReportMd] = useState<string | null>(
    initialSnapshot?.reportMd ?? null,
  );
  const [reportOpen, setReportOpen] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [stopping, setStopping] = useState(false);

  const streamCloseRef = useRef<(() => void) | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timelineRef = useRef<HTMLDivElement | null>(null);
  // drillId 的 ref 镜像：SSE onError 回调在 setDrillId 之前的渲染里创建，
  // 闭包拿不到最新 state，必须走 ref 才能触发断线轮询兜底。
  const drillIdRef = useRef<string | null>(initialSnapshot?.drillId ?? null);

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
        setStopping(false);
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
    setStopping(false);
    // 开启新一轮：清除上一轮快照，避免旧结果串场
    clearSnapshot();
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
      setReportMd(null);
      setReportOpen(false);
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

  /** 停止演练：防重复点击（stopping 期间按钮禁用），abort 幂等。 */
  const handleStop = useCallback(async () => {
    const id = drillIdRef.current;
    if (!id || stopping) return;
    setStopping(true);
    try {
      await cyberApi.abortDrill(id);
      // 编排器在阶段/轮边界中止，SSE 会继续收到 summary/done
    } catch (err) {
      setCyberError(
        err instanceof Error ? err.message : "Failed to abort drill",
      );
      setStopping(false);
    }
  }, [stopping, setCyberError]);

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

  // 结果持久化：drillId 存在时持续把最近一轮结果写入 sessionStorage，
  // 切 tab/刷新后恢复；开启新一轮时 handleStart 已清除旧快照
  useEffect(() => {
    if (!drillId) {
      clearSnapshot();
      return;
    }
    saveSnapshot({ drillId, phase, rounds, summary, reportMd });
  }, [drillId, phase, rounds, summary, reportMd]);

  // 卸载清理：关闭 SSE + 停止轮询
  useEffect(() => {
    return () => {
      streamCloseRef.current?.();
      drillIdRef.current = null;
      stopPolling();
    };
  }, [stopPolling]);

  // R15 中断恢复增强：恢复出的快照若缺少 summary（中断/中止场景），
  // 挂载时尝试从服务端补拉完整记录（后台线程可能已落盘）
  useEffect(() => {
    const id = drillIdRef.current;
    if (!id || summary) return;
    if (phase !== "done" && phase !== "aborted") return;
    let cancelled = false;
    cyberApi
      .getDrill(id)
      .then((rec) => {
        if (cancelled) return;
        if (rec.rounds.length > 0) setRounds(rec.rounds);
        if (rec.summary) {
          setSummary(rec.summary);
          setPhase(rec.convergence_code === "aborted" ? "aborted" : "done");
        } else if (rec.convergence_code) {
          setPhase(rec.convergence_code === "aborted" ? "aborted" : "done");
        }
      })
      .catch(() => {
        /* 服务端无记录则保持快照现状 */
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
            disabled={stopping}
          >
            {stopping ? "⏹ 停止中…" : "⏹ Stop"}
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

      {/* T3 收敛趋势图：≥2 轮才显示 */}
      {rounds.length >= 2 ? <TrendChart rounds={rounds} /> : null}

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
                    {/* T4 R10：端-边-云执行位置（自适应调度可视化） */}
                    {round.phase ? (
                      <div className="cyber-placement">
                        <h5 className="cyber-panel__subtitle">
                          ⚡ 执行位置 · 端-边-云自适应调度
                        </h5>
                        <div className="cyber-placement__rows">
                          {(["red", "blue", "purple"] as const).map((p) => {
                            const ph = round.phase?.[p];
                            if (!ph) return null;
                            const tier =
                              TIER_META[ph.tier] ??
                              ({ label: ph.tier, cls: "cloud", icon: "?" } as const);
                            return (
                              <div key={p} className="cyber-placement__row">
                                <span className="cyber-placement__phase">
                                  {PHASE_META[p].label}
                                  <em>{PHASE_META[p].desc}</em>
                                </span>
                                <span
                                  className={`cyber-placement__badge cyber-placement__badge--${tier.cls}`}
                                >
                                  {tier.icon} {tier.label}
                                </span>
                                <span className="cyber-placement__model">
                                  {ph.model_id}
                                </span>
                                <span className="cyber-placement__reason">
                                  {ph.reason}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : null}
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
                        {/* T6 量化指标：该轮防御覆盖率 + 安全评分 */}
                        {round.blue.ok ? (
                          (() => {
                            const atk = [
                              ...new Set(
                                (round.red.steps as any[])
                                  .map((s) => s.technique)
                                  .filter(Boolean),
                              ),
                            ];
                            const det = [
                              ...new Set(
                                (round.blue.alerts as any[])
                                  .map((a) => a.technique)
                                  .filter(Boolean),
                              ),
                            ];
                            const cov = atk.length
                              ? Math.round(
                                  (atk.filter((t) => det.includes(t)).length /
                                    atk.length) *
                                    100,
                                )
                              : null;
                            const strength = round.blue.alerts.length
                              ? Math.min(
                                  1,
                                  ((round.blue.plan?.actions as any[])?.length ??
                                    0) / round.blue.alerts.length,
                                )
                              : 0;
                            const sc =
                              cov != null
                                ? Math.round(cov * 0.6 + strength * 40)
                                : Math.round(strength * 40);
                            const cls =
                              sc >= 80 ? "success" : sc >= 60 ? "warning" : "danger";
                            return (
                              <p className="cyber-panel__text cyber-metrics">
                                防御覆盖率{" "}
                                <strong className={`cyber-score cyber-score--${cls}`}>
                                  {cov != null ? `${cov}%` : "—"}
                                </strong>{" "}
                                · 安全评分{" "}
                                <strong className={`cyber-score cyber-score--${cls}`}>
                                  {sc}
                                </strong>
                                <span className="cyber-metrics__hint">
                                  （{atk.length} 技法 vs {det.length} 检测技法）
                                </span>
                              </p>
                            );
                          })()
                        ) : null}
                        {round.blue.plan?.actions ? (
                          <ul className="cyber-issue-list cyber-issue-list--review">
                            {(round.blue.plan.actions as any[]).map(
                              (a: any, i: number) => {
                                // 兼容字符串与对象两种 action 结构，避免 [object Object]
                                let text: string;
                                if (typeof a === "string") {
                                  text = a;
                                } else {
                                  const head = [a.kind, a.target]
                                    .filter(Boolean)
                                    .join(" → ");
                                  text = head
                                    ? a.rationale
                                      ? `${head}：${a.rationale}`
                                      : head
                                    : JSON.stringify(a);
                                }
                                return (
                                  <li
                                    key={a.action_id ?? i}
                                    className="cyber-issue cyber-issue--review"
                                  >
                                    <span className="cyber-issue__icon">i</span>
                                    <span>{text}</span>
                                  </li>
                                );
                              },
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
          {(phase === "done" || phase === "aborted") && drillId ? (
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
