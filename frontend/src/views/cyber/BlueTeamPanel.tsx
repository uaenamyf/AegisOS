// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 BlueTeamPanel——蓝队防御仪表盘（告警列表 + 响应计划 + 执行状态）
// changelog: 2026-09-06 R15 —— 中断恢复(localStorage 缓存) + 可观测(耗时/agent trace)
//   + 可视化(告警严重度分布条 / 响应动作类型分布条)
// changelog: 2026-09-06 T1 —— SSE 流式渐进展示：四阶段(检测/分诊/狩猎/规划)逐步出结果

import { useCallback, useEffect, useRef, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import { systemApi } from "@/services/api/system";
import type { BlueDefenseResponse, BlueDefenseStreamEvent } from "@/protocol/types";
import { AgentTraceSection } from "./AgentTraceSection";

const LAST_CACHE_KEY = "aegis.blueDefense.v2.last";

// T1：蓝队四阶段语义（与后端流式阶段名对齐：detect/triage/hunt/ir）
const BLUE_STAGE_LABELS: Record<string, string> = {
  detect: "入侵检测",
  triage: "告警分诊",
  hunt: "威胁狩猎",
  ir: "响应规划",
};
const BLUE_STAGE_ORDER = ["detect", "triage", "hunt", "ir"];

/**
 * 蓝队防御面板。
 *
 * 展示蓝队防御链产出：告警列表（带严重度徽章）、分类后的告警、
 * 安全假设、以及蓝队响应计划（含动作和置信度）。
 *
 * R15 增强：
 * - 中断恢复：结果持久化到 localStorage，刷新/切 tab 后自动恢复并标注来源；
 *   同模式 + 同输入再次执行直接秒回（真实模式演示友好）。
 * - 可观测：执行耗时 + 逐 agent 输入输出追踪（detector→triage→threat_hunt→ir_planner）。
 * - 可视化：告警严重度分布条 + 响应动作类型分布条。
 *
 * T1 增强：
 * - SSE 流式渐进展示：四阶段（入侵检测→告警分诊→威胁狩猎→响应规划）
 *   逐步出结果，不再干等一次性返回；与红队面板流式体验对齐。
 */
export function BlueTeamPanel() {
  const blueDefenseResult = useAppStore((s) => s.blueDefenseResult);
  const redAttackResult = useAppStore((s) => s.redAttackResult);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setBlueDefenseResult = useAppStore((s) => s.setBlueDefenseResult);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const [eventInput, setEventInput] = useState("");
  const [cacheMode, setCacheMode] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  // T1 流式状态：streamStage=当前阶段 / stageDone=已完成阶段 / partial=部分产出
  const [streamStage, setStreamStage] = useState<string | null>(null);
  const [stageDone, setStageDone] = useState<string[]>([]);
  const [partial, setPartial] = useState<BlueDefenseResponse | null>(null);
  const closeStreamRef = useRef<(() => void) | null>(null);
  const startRef = useRef<number>(0);

  // 组件卸载时中止进行中的流
  useEffect(() => {
    return () => closeStreamRef.current?.();
  }, []);

  // 中断恢复：挂载时若 store 无结果，从 localStorage 恢复最近一次蓝队结果
  useEffect(() => {
    if (blueDefenseResult) return;
    try {
      const raw = localStorage.getItem(LAST_CACHE_KEY);
      if (raw) {
        const snap = JSON.parse(raw) as {
          mode: string;
          input: string;
          result: BlueDefenseResponse;
        };
        setBlueDefenseResult(snap.result);
        setCacheMode(`缓存 ${snap.mode}`);
        if (snap.input) setEventInput(snap.input);
      }
    } catch {
      /* 缓存损坏时忽略 */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDefend = useCallback(async () => {
    let eventStream: Record<string, unknown>[] | undefined;
    if (eventInput.trim()) {
      try {
        eventStream = JSON.parse(eventInput);
      } catch {
        eventStream = [{ event: eventInput.trim() }];
      }
    }

    closeStreamRef.current?.();
    setCyberLoading(true);
    setCyberError(null);
    setElapsed(null);
    setStreamStage(null);
    setStageDone([]);
    setPartial(null);
    setCacheMode(null);
    startRef.current = Date.now();

    // 精确缓存：同 mode + 同输入命中直接秒回
    let mode = "mock";
    try {
      const m = await systemApi.getMode();
      mode = m.mode;
    } catch {
      /* 后端离线时按 mock 处理 */
    }
    const inputSig = eventInput.trim() || "default";
    const exactKey = `aegis.blueDefense.v2.${mode}.${inputSig}`;
    try {
      const raw = localStorage.getItem(exactKey);
      if (raw) {
        setBlueDefenseResult(JSON.parse(raw) as BlueDefenseResponse);
        setCacheMode(`缓存 ${mode}`);
        setCyberLoading(false);
        setElapsed(0);
        return;
      }
    } catch {
      /* 缓存损坏时忽略，重新执行 */
    }

    // SSE 流式执行：四阶段逐步出结果
    closeStreamRef.current = cyberApi.blueDefenseStream(
      { event_stream: eventStream },
      (ev: BlueDefenseStreamEvent) => {
        if (ev.name === "stage_start") {
          setStreamStage(String(ev.data.stage));
        } else if (ev.name === "stage_done") {
          const stage = String(ev.data.stage);
          setStageDone((prev) => (prev.includes(stage) ? prev : [...prev, stage]));
          setPartial((prev) => {
            const next = { ...(prev ?? {}) } as BlueDefenseResponse;
            if (stage === "detect") next.alerts = ev.data.alerts ?? [];
            else if (stage === "triage") next.triaged = ev.data.triaged ?? [];
            else if (stage === "hunt") next.hypotheses = ev.data.hypotheses ?? [];
            else if (stage === "ir") next.plan = ev.data.plan ?? {};
            return next;
          });
        } else if (ev.name === "done") {
          const result = ev.data as unknown as BlueDefenseResponse;
          setBlueDefenseResult(result);
          setPartial(null);
          setStreamStage(null);
          setStageDone([...BLUE_STAGE_ORDER]);
          setCyberLoading(false);
          setElapsed((Date.now() - startRef.current) / 1000);
          try {
            localStorage.setItem(exactKey, JSON.stringify(result));
            localStorage.setItem(
              LAST_CACHE_KEY,
              JSON.stringify({ mode, input: eventInput.trim(), result }),
            );
          } catch {
            /* 存储配额等异常时忽略 */
          }
        } else if (ev.name === "defense_error") {
          setCyberError(String((ev.data as any)?.message ?? "defense stream failed"));
          setStreamStage(null);
          setCyberLoading(false);
          setElapsed((Date.now() - startRef.current) / 1000);
        }
      },
      (err) => {
        setCyberError(err?.message ?? "defense stream failed");
        setStreamStage(null);
        setCyberLoading(false);
        setElapsed((Date.now() - startRef.current) / 1000);
      },
    );
  }, [eventInput, setBlueDefenseResult, setCyberLoading, setCyberError]);

  // 数据源：完整结果优先，流式中用部分产出渐进渲染
  const display: BlueDefenseResponse | null = blueDefenseResult ?? partial;
  const alerts = display?.alerts ?? [];
  const triaged = display?.triaged ?? [];
  const hypotheses = display?.hypotheses ?? [];
  const plan = display?.plan ?? {};

  if (!display && !cyberLoading && streamStage == null) {
    return (
      <div className="cyber-panel cyber-panel--empty">
        <p className="cyber-panel__hint">
          No defense response yet. Enter an event stream (JSON or plain text)
          and click <strong>Execute Blue Defense</strong>. For full
          red→blue→purple auto cycling (one button, multi-round), switch to
          the <strong>Auto Drill</strong> tab.
        </p>
        <textarea
          className="cyber-view__textarea"
          value={eventInput}
          onChange={(e) => setEventInput(e.target.value)}
          placeholder='[{"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]'
          rows={3}
          disabled={cyberLoading}
        />
        <button
          className="cyber-view__btn cyber-view__btn--primary"
          onClick={() => void handleDefend()}
          disabled={cyberLoading}
        >
          {cyberLoading ? "Executing…" : "Execute Blue Defense"}
        </button>
      </div>
    );
  }

  const planActions: any[] = plan?.actions ?? [];
  const confidence: number = plan?.confidence ?? 0;

  // T6 量化指标：防御覆盖率 + 安全评分
  // 覆盖率 = 红队攻击技法 ∩ 蓝队告警技法 / 红队攻击技法（按技法编号对齐）
  const redSteps: any[] = redAttackResult?.chain?.steps ?? [];
  const attackTechs = [...new Set(redSteps.map((s) => s.technique).filter(Boolean))];
  const detectTechs = [...new Set(alerts.map((a) => a.technique).filter(Boolean))];
  const coveredTechs = attackTechs.filter((t) => detectTechs.includes(t));
  const coveragePct =
    attackTechs.length > 0
      ? Math.round((coveredTechs.length / attackTechs.length) * 100)
      : null; // 未跑红队时无攻击基线
  // 处置强度 = min(1, 动作数 / 告警数)；安全评分 = 覆盖率×60 + 处置强度×40
  const responseStrength =
    alerts.length > 0 ? Math.min(1, planActions.length / alerts.length) : 0;
  const score =
    coveragePct != null
      ? Math.round(coveragePct * 0.6 + responseStrength * 40)
      : Math.round(responseStrength * 40);
  const scoreCls = score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
  const coverageCls =
    coveragePct == null
      ? "warning"
      : coveragePct >= 80
        ? "success"
        : coveragePct >= 60
          ? "warning"
          : "danger";

  const severityColor = (sev: string): string => {
    switch (sev) {
      case "critical": return "danger";
      case "high": return "danger";
      case "medium": return "warning";
      case "low": return "success";
      default: return "warning";
    }
  };

  // R15 可视化：告警严重度分布
  const sevCount: Record<string, number> = {};
  alerts.forEach((a) => {
    const k = a.severity ?? "unknown";
    sevCount[k] = (sevCount[k] ?? 0) + 1;
  });
  const sevOrder = ["critical", "high", "medium", "low"];
  const sevClass = (k: string) =>
    k === "critical" || k === "high" ? "danger" : k === "medium" ? "warning" : "success";

  // R15 可视化：响应动作类型分布
  const kindCount: Record<string, number> = {};
  planActions.forEach((a: any) => {
    const k = a.kind ?? "other";
    kindCount[k] = (kindCount[k] ?? 0) + 1;
  });
  const kindOrder = ["block", "isolate", "patch", "monitor", "decoy", "other"];

  return (
    <div className="cyber-panel">
      {/* Action bar */}
      <div className="cyber-panel__actions">
        <textarea
          className="cyber-view__textarea cyber-view__textarea--inline"
          value={eventInput}
          onChange={(e) => setEventInput(e.target.value)}
          placeholder='[{"event": "ssh-brute-force"}]'
          rows={1}
          disabled={cyberLoading}
        />
        <button
          className="cyber-view__btn cyber-view__btn--primary"
          onClick={() => void handleDefend()}
          disabled={cyberLoading}
        >
          {streamStage
            ? `执行中:${BLUE_STAGE_LABELS[streamStage] ?? streamStage}…`
            : cyberLoading
              ? "Executing…"
              : "Re-execute Blue Defense"}
        </button>
      </div>

      {/* R15 执行元信息：耗时 / 缓存来源 */}
      <div className="cyber-meta">
        {elapsed != null ? (
          <span className="cyber-meta__chip">⏱ 执行耗时 {elapsed.toFixed(1)}s</span>
        ) : null}
        {cacheMode ? (
          <span className="cyber-meta__chip cyber-meta__chip--warn">
            ↻ 已从浏览器缓存恢复（{cacheMode}）
          </span>
        ) : null}
      </div>

      {/* T1：四阶段渐进指示器（流式中实时反映，完成后保留全部 ✓） */}
      {streamStage != null || stageDone.length > 0 ? (
        <div className="cyber-attack__stages">
          {BLUE_STAGE_ORDER.map((s) => {
            const isDone = stageDone.includes(s);
            const isActive = streamStage === s;
            return (
              <span
                key={s}
                className={`cyber-attack__stage ${
                  isDone
                    ? "cyber-attack__stage--done"
                    : isActive
                      ? "cyber-attack__stage--active"
                      : ""
                }`}
              >
                {isDone ? "✓" : isActive ? "●" : "○"} {BLUE_STAGE_LABELS[s]}
              </span>
            );
          })}
        </div>
      ) : null}

      {/* Stats */}
      <div className="cyber-panel__stats">
        <span className="cyber-stat">
          <span className="cyber-stat__value">{alerts.length}</span>
          <span className="cyber-stat__label">alerts</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">{triaged.length}</span>
          <span className="cyber-stat__label">triaged</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">{hypotheses.length}</span>
          <span className="cyber-stat__label">hypotheses</span>
        </span>
        <span className="cyber-stat">
          <span className="cyber-stat__value">{planActions.length}</span>
          <span className="cyber-stat__label">actions</span>
        </span>
        {/* T6 量化指标：防御覆盖率 + 安全评分 */}
        <span className="cyber-stat">
          <span className={`cyber-stat__value cyber-stat__value--${coverageCls}`}>
            {coveragePct != null ? `${coveragePct}%` : "—"}
          </span>
          <span className="cyber-stat__label">
            {coveragePct != null ? "coverage" : "coverage (run red first)"}
          </span>
        </span>
        <span className="cyber-stat">
          <span className={`cyber-stat__value cyber-stat__value--${scoreCls}`}>
            {score}
          </span>
          <span className="cyber-stat__label">security score</span>
        </span>
      </div>

      {/* R15 可视化：告警严重度分布 */}
      {alerts.length > 0 ? (
        <div className="cyber-dist">
          {sevOrder.filter((k) => sevCount[k]).map((k) => (
            <div key={k} className="cyber-dist__row">
              <span className="cyber-dist__label">{k}</span>
              <div className="cyber-dist__track">
                <div
                  className={`cyber-dist__fill cyber-dist__fill--${sevClass(k)}`}
                  style={{ width: `${(sevCount[k] / alerts.length) * 100}%` }}
                />
              </div>
              <span className="cyber-dist__count">{sevCount[k]}</span>
            </div>
          ))}
        </div>
      ) : null}

      {/* R15 可视化：响应动作类型分布 */}
      {planActions.length > 0 ? (
        <div className="cyber-dist">
          {kindOrder.filter((k) => kindCount[k]).map((k) => (
            <div key={k} className="cyber-dist__row">
              <span className="cyber-dist__label">{k}</span>
              <div className="cyber-dist__track">
                <div
                  className="cyber-dist__fill cyber-dist__fill--accent"
                  style={{ width: `${(kindCount[k] / planActions.length) * 100}%` }}
                />
              </div>
              <span className="cyber-dist__count">{kindCount[k]}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="cyber-panel__grid">
        {/* Alerts column */}
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">Alerts</h4>
          {alerts.length === 0 ? (
            <p className="cyber-panel__empty">No alerts generated.</p>
          ) : (
            <ul className="cyber-alert-list">
              {alerts.map((alert) => (
                <li key={alert.alert_id} className="cyber-alert">
                  <div className="cyber-alert__header">
                    <span className="cyber-alert__id">{alert.alert_id}</span>
                    <span className={`badge badge--${severityColor(alert.severity ?? "low")}`}>
                      {alert.severity}
                    </span>
                  </div>
                  <div className="cyber-alert__meta">
                    <span>{alert.src} → {alert.dst}</span>
                    {alert.technique ? <span className="cyber-alert__tech">{alert.technique}</span> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Response plan column */}
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">
            Response Plan
            <span className="cyber-confidence">
              {(confidence * 100).toFixed(0)}% confidence
            </span>
          </h4>
          {planActions.length === 0 ? (
            <p className="cyber-panel__empty">No response actions.</p>
          ) : (
            <ul className="cyber-action-list">
              {planActions.map((action: any) => (
                <li key={action.action_id ?? action.kind} className="cyber-action">
                  <span className={`cyber-action__kind cyber-action__kind--${action.kind}`}>
                    {action.kind}
                  </span>
                  <div className="cyber-action__body">
                    <span className="cyber-action__target">{action.target}</span>
                    {action.rationale ? (
                      <span className="cyber-action__rationale">{action.rationale}</span>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
          {plan?.rollback && Object.keys(plan.rollback).length > 0 ? (
            <div className="cyber-rollback">
              <span className="cyber-rollback__label">Rollback:</span>
              <code className="cyber-rollback__code">
                {JSON.stringify(plan.rollback)}
              </code>
            </div>
          ) : null}
        </div>
      </div>

      {/* Hypotheses */}
      {hypotheses.length > 0 ? (
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">Security Hypotheses</h4>
          <ul className="cyber-hypothesis-list">
            {hypotheses.map((h, i) => (
              <li key={i} className="cyber-hypothesis">
                <span className="cyber-hypothesis__icon">ⓘ</span>
                <span className="cyber-hypothesis__text">
                  {typeof h === "string" ? h : JSON.stringify(h)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* R15 可观测性：逐 agent 输入输出追踪 */}
      <AgentTraceSection trace={display?.agent_trace} />
    </div>
  );
}
