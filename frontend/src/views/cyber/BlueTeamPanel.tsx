// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 BlueTeamPanel——蓝队防御仪表盘（告警列表 + 响应计划 + 执行状态）
// changelog: 2026-09-06 R15 —— 中断恢复(localStorage 缓存) + 可观测(耗时/agent trace)
//   + 可视化(告警严重度分布条 / 响应动作类型分布条)

import { useCallback, useEffect, useRef, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import { systemApi } from "@/services/api/system";
import type { BlueDefenseResponse } from "@/protocol/types";
import { AgentTraceSection } from "./AgentTraceSection";

const LAST_CACHE_KEY = "aegis.blueDefense.v2.last";

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
 */
export function BlueTeamPanel() {
  const blueDefenseResult = useAppStore((s) => s.blueDefenseResult);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setBlueDefenseResult = useAppStore((s) => s.setBlueDefenseResult);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const [eventInput, setEventInput] = useState("");
  const [cacheMode, setCacheMode] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const startRef = useRef<number>(0);

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

    setCyberLoading(true);
    setCyberError(null);
    setElapsed(null);
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

    try {
      const result = await cyberApi.blueDefense({ event_stream: eventStream });
      setBlueDefenseResult(result);
      setCacheMode(null);
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
    } catch (err) {
      setCyberError(err instanceof Error ? err.message : "Blue defense failed");
      setElapsed((Date.now() - startRef.current) / 1000);
    } finally {
      setCyberLoading(false);
    }
  }, [eventInput, setBlueDefenseResult, setCyberLoading, setCyberError]);

  if (!blueDefenseResult) {
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

  const { alerts, triaged, hypotheses, plan } = blueDefenseResult;
  const planActions: any[] = plan?.actions ?? [];
  const confidence: number = plan?.confidence ?? 0;

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
          {cyberLoading ? "Executing…" : "Re-execute Blue Defense"}
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
      <AgentTraceSection trace={blueDefenseResult.agent_trace} />
    </div>
  );
}
