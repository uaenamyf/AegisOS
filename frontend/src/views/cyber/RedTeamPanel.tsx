// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 RedTeamPanel——红队攻击链可视化（资产→漏洞→攻击链 DAG）

import { useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";

/**
 * 红队攻击链面板。
 *
 * 展示攻击链 DAG：资产节点 → 漏洞发现 → 攻击步骤（带 from→to 连线）。
 * 使用自定义 SVG 渲染节点和连线，无需额外依赖。
 */
export function RedTeamPanel() {
  const currentRange = useAppStore((s) => s.currentRange);
  const redAttackResult = useAppStore((s) => s.redAttackResult);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setRedAttackResult = useAppStore((s) => s.setRedAttackResult);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const handleAttack = useCallback(async () => {
    const target = currentRange?.target_range ?? "10.0.0.0/24";
    setCyberLoading(true);
    setCyberError(null);
    try {
      const result = await cyberApi.redAttack({ target_range: target });
      setRedAttackResult(result);
    } catch (err) {
      setCyberError(err instanceof Error ? err.message : "Red attack failed");
    } finally {
      setCyberLoading(false);
    }
  }, [currentRange, setRedAttackResult, setCyberLoading, setCyberError]);

  if (!redAttackResult) {
    return (
      <div className="cyber-panel cyber-panel--empty">
        <p className="cyber-panel__hint">
          No attack chain yet. Click <strong>Execute Red Attack</strong> to
          generate an attack chain DAG.
        </p>
        <button
          className="cyber-view__btn cyber-view__btn--danger"
          onClick={() => void handleAttack()}
          disabled={cyberLoading}
        >
          {cyberLoading ? "Executing…" : "Execute Red Attack"}
        </button>
      </div>
    );
  }

  const { assets, findings, chain } = redAttackResult;
  const steps: any[] = chain.steps ?? [];

  // Build DAG layout positions
  const assetPositions: Record<string, { x: number; y: number }> = {};
  const colWidth = 200;
  const rowHeight = 80;
  const padding = 40;

  assets.forEach((asset, i) => {
    assetPositions[asset.asset_id] = {
      x: padding,
      y: padding + i * rowHeight,
    };
  });

  // Steps laid out horizontally as columns
  steps.forEach((step: any, i) => {
    const fromY = assetPositions[step.from_asset]?.y ?? padding;
    assetPositions[step.step_id] = {
      x: padding + colWidth * (i + 1),
      y: fromY,
    };
  });

  const svgWidth = Math.max(600, padding + colWidth * (steps.length + 1) + padding);
  const svgHeight = Math.max(200, padding + assets.length * rowHeight + padding);

  return (
    <div className="cyber-panel">
      {/* Action bar */}
      <div className="cyber-panel__actions">
        <button
          className="cyber-view__btn cyber-view__btn--danger"
          onClick={() => void handleAttack()}
          disabled={cyberLoading}
        >
          {cyberLoading ? "Executing…" : "Re-execute Red Attack"}
        </button>
        <div className="cyber-panel__stats">
          <span className="cyber-stat">
            <span className="cyber-stat__value">{assets.length}</span>
            <span className="cyber-stat__label">assets</span>
          </span>
          <span className="cyber-stat">
            <span className="cyber-stat__value">{findings.length}</span>
            <span className="cyber-stat__label">vulns</span>
          </span>
          <span className="cyber-stat">
            <span className="cyber-stat__value">{steps.length}</span>
            <span className="cyber-stat__label">steps</span>
          </span>
          <span className="cyber-stat">
            <span className="cyber-stat__value">{chain.status ?? "—"}</span>
            <span className="cyber-stat__label">status</span>
          </span>
        </div>
      </div>

      {/* DAG Visualization */}
      <div className="cyber-dag">
        <svg
          className="cyber-dag__svg"
          width="100%"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        >
          {/* Edges (attack steps) */}
          {steps.map((step: any) => {
            const fromPos = assetPositions[step.from_asset];
            const toPos = assetPositions[step.to_asset];
            if (!fromPos || !toPos) return null;
            const midX = (fromPos.x + toPos.x) / 2;
            return (
              <g key={step.step_id}>
                <path
                  d={`M ${fromPos.x + 80} ${fromPos.y + 16} C ${midX} ${fromPos.y}, ${midX} ${toPos.y}, ${toPos.x} ${toPos.y + 16}`}
                  fill="none"
                  stroke="var(--danger)"
                  strokeWidth="2"
                  markerEnd="url(#arrow-red)"
                  opacity={step.success ? 1 : 0.4}
                />
                <text
                  x={midX}
                  y={(fromPos.y + toPos.y) / 2 - 8}
                  fill="var(--text-secondary)"
                  fontSize="10"
                  textAnchor="middle"
                >
                  {step.technique}
                </text>
              </g>
            );
          })}

          {/* Asset nodes */}
          {assets.map((asset) => {
            const pos = assetPositions[asset.asset_id];
            if (!pos) return null;
            return (
              <g key={asset.asset_id} transform={`translate(${pos.x}, ${pos.y})`}>
                <rect width="80" height="32" rx="6" fill="var(--bg-tertiary)" stroke="var(--accent)" strokeWidth="1.5" />
                <text x="40" y="14" fill="var(--text-primary)" fontSize="10" textAnchor="middle" fontWeight="600">
                  {asset.asset_id}
                </text>
                <text x="40" y="26" fill="var(--text-muted)" fontSize="9" textAnchor="middle">
                  {asset.os || asset.host}
                </text>
              </g>
            );
          })}

          {/* Step nodes */}
          {steps.map((step: any) => {
            const pos = assetPositions[step.step_id];
            if (!pos) return null;
            return (
              <g key={step.step_id} transform={`translate(${pos.x}, ${pos.y})`}>
                <rect width="80" height="32" rx="6" fill="var(--bg-secondary)" stroke="var(--danger)" strokeWidth="1.5" />
                <text x="40" y="14" fill="var(--text-primary)" fontSize="9" textAnchor="middle" fontWeight="600">
                  {step.to_asset}
                </text>
                <text x="40" y="26" fill="var(--text-muted)" fontSize="8" textAnchor="middle">
                  {step.success ? "✓ success" : "○ planned"}
                </text>
              </g>
            );
          })}

          <defs>
            <marker
              id="arrow-red"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
            >
              <polygon points="0 0, 8 4, 0 8" fill="var(--danger)" />
            </marker>
          </defs>
        </svg>
      </div>

      {/* Vulnerability findings table */}
      {findings.length > 0 ? (
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">Vulnerability Findings</h4>
          <div className="cyber-table">
            {findings.map((f) => (
              <div key={f.finding_id} className="cyber-table__row">
                <span className="cyber-table__cell cyber-table__cell--id">{f.finding_id}</span>
                <span className="cyber-table__cell cyber-table__cell--cve">{f.cve_id || "—"}</span>
                <span className="cyber-table__cell">{f.asset_id}</span>
                <span className="cyber-table__cell cyber-table__cell--score">
                  <span className={`cyber-score cyber-score--${(f.cvss ?? 0) >= 7 ? "high" : "med"}`}>
                    {(f.cvss ?? 0).toFixed(1)}
                  </span>
                </span>
                <span className="cyber-table__cell cyber-table__cell--surface">{f.attack_surface}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
