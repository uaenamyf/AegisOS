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

// T2: 资产类型推断（按服务/暴露面）——节点配色与图标
interface AssetTypeMeta {
  label: string;
  icon: string;
  color: string; // SVG stroke 色
  bg: string;    // SVG fill 色
}
const ASSET_TYPE_META: Record<string, AssetTypeMeta> = {
  web: { label: "Web", icon: "🖥", color: "#2e9e5b", bg: "#12241b" },
  db: { label: "DB", icon: "🗄", color: "#2f7de1", bg: "#122038" },
  cache: { label: "Cache", icon: "⚡", color: "#d9a13b", bg: "#2a2012" },
  server: { label: "Server", icon: "🖧", color: "#8a5cf6", bg: "#221a38" },
  other: { label: "Host", icon: "●", color: "#5a6b7d", bg: "#1a2230" },
};
function assetType(asset: any): AssetTypeMeta {
  const svc = (asset.services ?? []).join(" ").toLowerCase();
  const key = /mysql|postgres|mariadb|oracle/.test(svc)
    ? "db"
    : /redis|memcached|kafka/.test(svc)
      ? "cache"
      : /http|https|nginx|apache|tomcat/.test(svc)
        ? "web"
        : /ssh|smb|rdp|ftp/.test(svc)
          ? "server"
          : "other";
  return ASSET_TYPE_META[key];
}

// T2: 漏洞 cvss 评分 → 严重度配色
function cvssColor(cvss: number | undefined): string {
  if (cvss == null) return "#5a6b7d";
  if (cvss >= 9) return "#e05252"; // critical
  if (cvss >= 7) return "#e07b3a"; // high
  if (cvss >= 4) return "#d9a13b"; // medium
  return "#2e9e5b"; // low
}

// T2: 步骤编号徽章（①②③…，最多 20 步，超出用数字）
const STEP_NUMS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
  "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"];
function stepNum(i: number): string {
  return STEP_NUMS[i] ?? String(i + 1);
}

// T9: 攻击技法语义表（推理轨迹展示）——编号 → 中文名 / 战术阶段 / 推理依据
// 与 ATT&CK 战术语义一致（威胁情报本地库同源），前端内置、离线可用
interface TechniqueMeta {
  name: string;
  tactic: string;
  why: string;
}
const TECHNIQUE_META: Record<string, TechniqueMeta> = {
  T1110: {
    name: "暴力破解",
    tactic: "凭据访问",
    why: "目标服务暴露登录接口且未观察到账户锁定策略，直接尝试凭据爆破是获取合法访问的最快路径——以最小成本换取有效账户。",
  },
  T1059: {
    name: "命令与脚本解释器",
    tactic: "执行",
    why: "在已获得的会话内调用系统自带解释器执行脚本，复用合法程序规避检测，同时取得目标主机的命令执行能力。",
  },
  T1021: {
    name: "远程服务",
    tactic: "横向移动",
    why: "通过已控主机的远程管理服务建立到内网主机的通道，借用合法管理协议掩盖横向移动行为。",
  },
  T1210: {
    name: "利用远程服务漏洞",
    tactic: "横向移动",
    why: "目标主机暴露存在已知漏洞的远程服务，直接利用漏洞获取执行权限，无需额外凭据即可推进链路。",
  },
  T1190: {
    name: "利用公网应用漏洞",
    tactic: "初始访问",
    why: "边界应用暴露于公网且版本存在已知漏洞，作为初始突破点进入内网。",
  },
  T1485: {
    name: "数据销毁",
    tactic: "影响",
    why: "达成目标后销毁关键数据，制造最大影响并延缓取证。",
  },
  T1078: {
    name: "有效账户",
    tactic: "防御规避",
    why: "复用合法账户凭据，以正常身份活动规避检测。",
  },
  T1562: {
    name: "防御规避",
    tactic: "防御规避",
    why: "禁用或干扰目标主机的安全防护，为后续攻击动作铺路。",
  },
  T1046: {
    name: "网络服务扫描",
    tactic: "侦察",
    why: "探测目标网段开放的服务与端口，定位下一步可利用的攻击面。",
  },
  T1083: {
    name: "文件与目录发现",
    tactic: "侦察",
    why: "枚举目标主机文件系统，定位高价值数据与配置信息。",
  },
};

/** 技法编号 → 语义；未收录时用通用兜底模板 */
function techMeta(technique: string): TechniqueMeta {
  return (
    TECHNIQUE_META[technique] ?? {
      name: technique,
      tactic: "未收录",
      why: `针对目标资产暴露面选取的下一步攻击技法（${technique}），用于推进攻击链路向最终目标靠近。`,
    }
  );
}

/** 攻击链整体推理摘要：由步骤序列自动拼接 */
function buildChainSummary(steps: any[]): string {
  if (steps.length === 0) return "";
  const first = steps[0];
  const last = steps[steps.length - 1];
  const moves = steps.length - 1;
  return `攻击链从「${first.from_asset}」突破，依次执行 ${steps.length} 个攻击步骤${
    moves > 0 ? `、经 ${moves} 次横向移动` : ""
  }，最终抵达目标「${last.to_asset}」；以 ${
    techMeta(last.technique).name
  }（${last.technique}）技法收尾，形成完整的 初始访问 → 横向移动 → 目标控制 链路。`;
}

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
          暂无攻击链结果。点击下方按钮直接运行红队攻击链（侦察 → 漏洞 → 攻击链）；
          完整多轮对抗请到「自动演练」。
        </p>
        <button
          className="cyber-view__btn cyber-view__btn--danger"
          onClick={() => void handleAttack()}
          disabled={cyberLoading}
        >
          ▶ 运行红队攻击
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
  // T2: 底部预留 48px 给漏洞严重度徽章，避免节点下方的徽章被裁切
  const svgHeight = Math.max(200, padding + assets.length * rowHeight + padding + 48);

  return (
    <div className="cyber-panel">
      {/* Action bar */}
      <div className="cyber-panel__actions">
        <button
          className="cyber-view__btn cyber-view__btn--danger"
          onClick={() => void handleAttack()}
          disabled={cyberLoading}
        >
          {cyberLoading ? "执行中…" : "▶ 重新运行"}
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
          {steps.map((step: any, si: number) => {
            const fromPos = assetPositions[step.from_asset];
            const toPos = assetPositions[step.to_asset];
            if (!fromPos || !toPos) return null;
            const midX = (fromPos.x + toPos.x) / 2;
            const midY = (fromPos.y + toPos.y) / 2;
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
                {/* T2: 步骤编号徽章 */}
                <circle
                  cx={midX - 34}
                  cy={midY - 8}
                  r="8"
                  fill="var(--danger)"
                />
                <text
                  x={midX - 34}
                  y={midY - 5}
                  fill="#fff"
                  fontSize="9"
                  fontWeight="700"
                  textAnchor="middle"
                >
                  {stepNum(si)}
                </text>
                <text
                  x={midX}
                  y={midY + 8}
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
            const t = assetType(asset);
            const vulns = findings.filter((f: any) => f.asset_id === asset.asset_id);
            return (
              <g key={asset.asset_id} transform={`translate(${pos.x}, ${pos.y})`}>
                <rect width="80" height="32" rx="6" fill={t.bg} stroke={t.color} strokeWidth="1.5" />
                <text x="6" y="14" fontSize="10">
                  {t.icon}
                </text>
                <text x="40" y="14" fill="var(--text-primary)" fontSize="10" textAnchor="middle" fontWeight="600">
                  {asset.asset_id}
                </text>
                <text x="40" y="26" fill="var(--text-muted)" fontSize="9" textAnchor="middle">
                  {t.label} · {asset.os || asset.host}
                </text>
                {/* T2: 漏洞严重度徽章（cvss 配色） */}
                {vulns.length > 0 ? (
                  <g transform="translate(0, 34)">
                    {vulns.slice(0, 3).map((v: any, vi: number) => (
                      <g key={v.finding_id ?? vi} transform={`translate(${vi * 27}, 0)`}>
                        <rect width="25" height="12" rx="6" fill={cvssColor(v.cvss)} opacity="0.9" />
                        <text x="12.5" y="9" fill="#fff" fontSize="7" textAnchor="middle" fontWeight="700">
                          {v.cvss != null ? v.cvss.toFixed(1) : v.attack_surface?.slice(0, 5) ?? "?"}
                        </text>
                      </g>
                    ))}
                    {vulns.length > 3 ? (
                      <text x={vulns.slice(0, 3).length * 27 + 4} y="9" fill="var(--text-dim)" fontSize="7">
                        +{vulns.length - 3}
                      </text>
                    ) : null}
                  </g>
                ) : null}
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

      {/* T9：推理轨迹 · 攻击链路依据（比赛能力维度 e：展示中间决策过程与推理轨迹） */}
      {steps.length > 0 ? (
        <div className="cyber-reason">
          <h4 className="cyber-panel__subtitle">🧠 推理轨迹 · 攻击链路依据</h4>
          <p className="cyber-reason__summary">{buildChainSummary(steps)}</p>
          <div className="cyber-reason__list">
            {steps.map((step: any, i: number) => {
              const meta = techMeta(step.technique);
              return (
                <div key={step.step_id ?? i} className="cyber-reason__item">
                  <span className="cyber-reason__idx">{i + 1}</span>
                  <div className="cyber-reason__body">
                    <div className="cyber-reason__head">
                      <span className="cyber-reason__name">{meta.name}</span>
                      <span className="cyber-reason__tech">{step.technique}</span>
                      <span className="cyber-reason__tactic">{meta.tactic}</span>
                      <span className="cyber-reason__path">
                        {step.from_asset} → {step.to_asset}
                      </span>
                    </div>
                    <p className="cyber-reason__why">{meta.why}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

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
