// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 RedTeamPanel——红队攻击链可视化（资产→漏洞→攻击链 DAG）
// changelog: 2026-09-05 —— SSE 流式渐进展示（阶段指示器 + 部分结果逐步渲染）
//   + localStorage 持久缓存（同 mode + 同目标直接秒回）

import { useCallback, useEffect, useRef, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import { systemApi } from "@/services/api/system";
import type { RedAttackResponse } from "@/protocol/types";
import { AgentTraceSection } from "./AgentTraceSection";

const STAGE_LABELS: Record<string, string> = {
  recon: "侦察资产",
  vuln: "关联漏洞",
  exploit: "规划攻击链",
};

/**
 * 红队攻击链面板。
 *
 * 展示攻击链 DAG：资产节点 → 漏洞发现 → 攻击步骤（带 from→to 连线）。
 * 使用自定义 SVG 渲染节点和连线，无需额外依赖。
 *
 * 真实 LLM 模式一次完整演练需 30-60s（3 次串行模型调用），点击后通过
 * SSE 流式渐进展示：阶段指示器实时反映「侦察中 → 关联中 → 规划中」，
 * 各步产出（资产 / 漏洞 / 攻击链）逐步渲染，避免长时间白屏等待。
 * 同一模式 + 同一目标的演练结果持久化到 localStorage，再次点击秒回。
 */
export function RedTeamPanel() {
  const currentRange = useAppStore((s) => s.currentRange);
  const redAttackResult = useAppStore((s) => s.redAttackResult);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setRedAttackResult = useAppStore((s) => s.setRedAttackResult);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  // 流式阶段状态：streamStage=当前阶段 / partial=各阶段部分产出 / cacheMode=缓存来源
  const [streamStage, setStreamStage] = useState<string | null>(null);
  const [partial, setPartial] = useState<Record<string, any>>({});
  const [cacheMode, setCacheMode] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const closeStreamRef = useRef<(() => void) | null>(null);
  const startRef = useRef<number>(0);

  // 组件卸载时中止进行中的流
  useEffect(() => {
    return () => closeStreamRef.current?.();
  }, []);

  const handleAttack = useCallback(async () => {
    const target = currentRange?.target_range ?? "10.0.0.0/24";
    closeStreamRef.current?.();
    setCyberLoading(true);
    setCyberError(null);
    setStreamStage(null);
    setPartial({});
    setCacheMode(null);
    setElapsed(null);
    startRef.current = Date.now();

    // 1) 浏览器持久缓存：同 mode + 同目标命中直接秒回（真实模式演示友好）
    let mode = "mock";
    try {
      const m = await systemApi.getMode();
      mode = m.mode;
    } catch {
      /* 后端离线时按 mock 处理 */
    }
    const cacheKey = `aegis.redAttack.v2.${mode}.${target}`;
    try {
      const raw = localStorage.getItem(cacheKey);
      if (raw) {
        setRedAttackResult(JSON.parse(raw) as RedAttackResponse);
        setCacheMode(mode);
        setCyberLoading(false);
        return;
      }
    } catch {
      /* 缓存损坏时忽略，重新执行 */
    }

    // 2) SSE 流式渐进执行
    const close = cyberApi.redAttackStream(
      { target_range: target },
      (ev) => {
        if (ev.name === "stage_start") {
          setStreamStage(String(ev.data?.stage ?? ""));
        } else if (ev.name === "stage_done") {
          const stage = String(ev.data?.stage ?? "");
          setPartial((prev) => ({ ...prev, [stage]: ev.data }));
          if (stage === "exploit") setStreamStage(null);
        } else if (ev.name === "done") {
          const result = ev.data as unknown as RedAttackResponse;
          setRedAttackResult(result);
          setStreamStage(null);
          setCyberLoading(false);
          setElapsed((Date.now() - startRef.current) / 1000);
          try {
            localStorage.setItem(cacheKey, JSON.stringify(result));
          } catch {
            /* 存储配额等异常时忽略 */
          }
        } else if (ev.name === "attack_error") {
          setCyberError(String((ev.data as any)?.message ?? "attack stream failed"));
          setStreamStage(null);
          setCyberLoading(false);
          setElapsed((Date.now() - startRef.current) / 1000);
        }
      },
      (err) => {
        setCyberError(err?.message ?? "attack stream failed");
        setStreamStage(null);
        setCyberLoading(false);
        setElapsed((Date.now() - startRef.current) / 1000);
      },
    );
    closeStreamRef.current = close;
  }, [currentRange, setRedAttackResult, setCyberLoading, setCyberError]);

  // 合并数据：有完整结果用完整结果；流式中用已到达的部分结果
  const assets = redAttackResult?.assets ?? (partial.recon?.assets as any[]) ?? [];
  const findings = redAttackResult?.findings ?? (partial.vuln?.findings as any[]) ?? [];
  const chain = redAttackResult?.chain ?? (partial.exploit?.chain as any) ?? { steps: [] };
  const steps: any[] = chain.steps ?? [];
  const hasAnyData = assets.length > 0 || findings.length > 0 || steps.length > 0;

  if (!hasAnyData && !cyberLoading && streamStage == null) {
    return (
      <div className="cyber-panel cyber-panel--empty">
        <p className="cyber-panel__hint">
          No attack chain yet. Click <strong>Execute Red Attack</strong> to
          generate an attack chain DAG. For full red→blue→purple auto
          cycling (one button, multi-round), switch to the{" "}
          <strong>Auto Drill</strong> tab.
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
          {cyberLoading ? "Executing…" : redAttackResult ? "Re-execute Red Attack" : "Execute Red Attack"}
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

      {/* 流式阶段指示器（渐进展示） */}
      {cyberLoading || Object.keys(partial).length > 0 ? (
        <div className="cyber-attack__stages">
          {Object.entries(STAGE_LABELS).map(([stage, label]) => {
            const done = Boolean(partial[stage]);
            const active = streamStage === stage;
            return (
              <span
                key={stage}
                className={`cyber-attack__stage${active ? " is-active" : ""}${done ? " is-done" : ""}`}
              >
                {done ? "✓ " : active ? "● " : "○ "}
                {label}
              </span>
            );
          })}
        </div>
      ) : null}

      {/* 缓存来源提示 */}
      {cacheMode ? (
        <div className="cyber-attack__cache-note">
          已从浏览器缓存加载（mode: {cacheMode}）—— 重新执行可调用真实模型
        </div>
      ) : null}

      {/* 执行耗时（R15 可观测性） */}
      {elapsed != null ? (
        <div className="cyber-meta">
          <span className="cyber-meta__chip">⏱ 执行耗时 {elapsed.toFixed(1)}s</span>
          <span className="cyber-meta__chip cyber-meta__chip--accent">
            mode: {cacheMode ?? "live"}
          </span>
        </div>
      ) : null}

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

      {/* R15 可观测性：逐 agent 输入输出追踪 */}
      <AgentTraceSection trace={redAttackResult?.agent_trace} />
    </div>
  );
}
