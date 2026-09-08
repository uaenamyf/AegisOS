// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 BlueTeamPanel——蓝队防御仪表盘（告警列表 + 响应计划 + 执行状态）

import { useCallback, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";

/**
 * 蓝队防御面板。
 *
 * 展示蓝队防御链产出：告警列表（带严重度徽章）、分类后的告警、
 * 安全假设、以及蓝队响应计划（含动作和置信度）。
 */
export function BlueTeamPanel() {
  const blueDefenseResult = useAppStore((s) => s.blueDefenseResult);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setBlueDefenseResult = useAppStore((s) => s.setBlueDefenseResult);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const [eventInput, setEventInput] = useState("");

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
    try {
      const result = await cyberApi.blueDefense({ event_stream: eventStream });
      setBlueDefenseResult(result);
    } catch (err) {
      setCyberError(err instanceof Error ? err.message : "Blue defense failed");
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
    </div>
  );
}
