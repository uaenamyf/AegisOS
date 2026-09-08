// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R5 新建 CyberDrillPanel——一键开始/停止 + SSE 轮次时间线 + 收敛总结报告

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";
import type {
  DrillEvent,
  DrillMeta,
  DrillRecord,
  DrillRound,
  DrillSummaryResponse,
} from "@/protocol/types";

type DrillPhase = "idle" | "running" | "done" | "aborted" | "error";

// R18e：资产 ID 归一化。缺口文本里的 asset-4 与战报里的 asset-004 必须归一，
// 否则缺口↔补攻永远匹配不上（截图里"未闭合"的根因之一）。
function normAsset(id: string): string {
  const m = /^asset-0*(\d+)$/i.exec(String(id ?? "").trim());
  return m ? `asset-${m[1].padStart(3, "0")}` : String(id ?? "").trim();
}

// R18e：技法编号提取（兼容 "T1190 (CVE-...) — 证据" 混合格式）。
function techIdOf(t: any): string {
  const m = /^(T\d+(?:\.\d+)?)/.exec(String(t ?? ""));
  return m ? m[1] : String(t ?? "");
}

// T3 收敛趋势图：每轮指标计算
// R18e：覆盖率分母改为「本轮全链技法」（累计攻击面），而非"本轮新增技法"。
// 旧算法分母只算新增，导致新增归零时覆盖率失真；累计口径才表达
// "蓝队对当前全部攻击面的检测覆盖程度"，配合 mock 检测规则逐轮建立，
// 曲线呈上升趋势（防御能力随对抗增强），而非之前越打越低。
function roundCoverage(round: DrillRound): number | null {
  const attackTechs = [
    ...new Set(
      (round.red.steps ?? [])
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
  const atk = [...new Set(attackTechs.map(techIdOf))];
  const det = [...new Set(detectTechs.map(techIdOf))];
  const covered = atk.filter((t) => det.includes(t)).length;
  return Math.round((covered / atk.length) * 100);
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

// T5 缺口闭环（R18g 重构）：只讲清「循环流程 + 三队职责 + 逐轮关键指标」。
// 旧版按「每条缺口」各自展开一条「挑缺口→补攻→判定」三段链；真实大模型每轮
// 7~9 条长缺口 ×N 轮 = 几十条链，再叠上跨轮贪婪配对，轮次来回穿插、蓝队缺席。
// 新版三条约束：
//   1) 顶部固定循环骶架，说明红→蓝→紫→反馈的职责与关联行为；
//   2) 逐轮严格按轮次升序，每轮只给关键指标，全文细节折叠按需展开；
//   3) 闭环配对只在「本轮红队补攻 ↔ 上轮紫队缺口」之间做，不跨多轮拉链。

interface RoundLoop {
  round: number;
  redNew: number;
  redTechs: string[];
  blueAlerts: number;
  blueTriaged: number;
  blueActions: string[];
  purpleValid: boolean;
  purpleIssues: number;
  purpleSeverity: string;
  issueTexts: string[];
  gapStep: number;
  gapChain: number;
  closed: number | null;
  prevIssues: number | null;
  prevRound: number | null;
  code: string;
}

// 缺口文本特征：资产号 / ATT&CK 技法号 / CVE（供与本轮红队新增步配对）。
function issueSig(text: string): { assets: string[]; techs: string[]; cves: string[] } {
  return {
    assets: [...new Set((text.match(/asset-\d+/gi) ?? []).map((s) => normAsset(s.toLowerCase())))]
      .filter(Boolean),
    techs: [...new Set(text.match(/T\d{4}(?:\.\d+)?/g) ?? [])],
    cves: [...new Set((text.match(/CVE-\d{4}-\d{4,7}/gi) ?? []).map((s) => s.toUpperCase()))],
  };
}

// 一个红队新增步是否“冲着这条缺口去的”：CVE / 技法 / 目标资产三者任命中其一。
function stepMatchesSig(
  step: any,
  sig: { assets: string[]; techs: string[]; cves: string[] },
): boolean {
  const raw = String(step?.technique ?? "");
  const tech = techIdOf(raw);
  const cves = (raw.match(/CVE-\d{4}-\d{4,7}/gi) ?? []).map((s) => s.toUpperCase());
  const to = normAsset(String(step?.to_asset ?? "").toLowerCase());
  if (sig.cves.some((c) => cves.includes(c))) return true;
  if (tech && sig.techs.includes(tech)) return true;
  if (to && sig.assets.includes(to)) return true;
  return false;
}

function buildRoundLoops(rounds: DrillRound[]): RoundLoop[] {
  const sorted = [...rounds].sort((a, b) => (a.round ?? 0) - (b.round ?? 0));
  return sorted.map((rd, idx) => {
    const red: any = rd.red ?? {};
    const blue: any = rd.blue ?? {};
    const purple: any = rd.purple ?? {};
    const critique: any = purple.critique ?? {};
    const issueTexts: string[] = (critique.issues ?? []).map((x: any) => String(x));
    const newSteps: any[] = red.new_steps ?? [];
    const redTechs = [
      ...new Set(newSteps.map((s: any) => techIdOf(s.technique)).filter(Boolean)),
    ];
    const kinds = ((blue.plan?.actions ?? []) as any[]).map(
      (a) => String(a.kind ?? a.action ?? "action"),
    );
    const blueActions = [
      ...new Set(kinds),
    ].map((k) => `${k}×${kinds.filter((x) => x === k).length}`);

    const prev: any = idx > 0 ? sorted[idx - 1] : null;
    let closed: number | null = null;
    let prevIssues: number | null = null;
    let prevRound: number | null = null;
    if (prev) {
      prevRound = prev.round ?? null;
      const prevTexts: string[] = ((prev.purple?.critique?.issues ?? []) as any[]).map(String);
      prevIssues = prevTexts.length;
      const sigs = prevTexts.map(issueSig);
      closed = sigs.filter((sg) => newSteps.some((s: any) => stepMatchesSig(s, sg))).length;
    }

    return {
      round: rd.round,
      redNew: newSteps.length,
      redTechs,
      blueAlerts: (blue.alerts ?? []).length,
      blueTriaged: blue.triaged_count ?? 0,
      blueActions,
      purpleValid: purple.valid === true,
      purpleIssues: issueTexts.length || (purple.new_issue_count ?? 0),
      purpleSeverity: String(critique.severity ?? ""),
      issueTexts,
      gapStep: issueTexts.filter((t) => /^\s*STEP-/i.test(t)).length,
      gapChain: issueTexts.filter((t) => !/^\s*STEP-/i.test(t)).length,
      closed,
      prevIssues,
      prevRound,
      code: rd.convergence_code ?? "",
    };
  });
}

/** 循环骶架：固定不变，说明三队在闭环里各自的任务与关联行为。 */
const LOOP_STAGES = [
  { key: "red", name: "红队·攻击", duty: "按上轮紫队缺口补攻，新增合法攻击步" },
  { key: "blue", name: "蓝队·防御", duty: "检测告警 → 分诊 → 下出处置动作" },
  { key: "purple", name: "紫队·判定", duty: "校验红蓝证据链一致性，输出缺口清单" },
  { key: "feedback", name: "缺口反馈", duty: "缺口回灌红队驱动下一轮；无缺口即收敛" },
] as const;

function GapClosureChart({ rounds }: { rounds: DrillRound[] }) {
  const [openRound, setOpenRound] = useState<number | null>(null);
  if (rounds.length < 2) return null;

  const loops = buildRoundLoops(rounds);
  const totalGaps = loops.reduce((n, l) => n + l.purpleIssues, 0);
  const closedTotal = loops.reduce((n, l) => n + (l.closed ?? 0), 0);
  const last = loops[loops.length - 1];
  if (!last) return null;

  return (
    <div className="cyber-closure">
      <h4 className="cyber-panel__subtitle">
        🔗 缺口闭环 · 一轮一次的对抗演化循环
      </h4>

      {/* ① 循环骶架：三队职责与关联行为 */}
      <div className="cyber-loop__cycle">
        {LOOP_STAGES.map((s, i) => (
          <Fragment key={s.key}>
            <div className={`cyber-loop__node cyber-loop__node--${s.key}`}>
              <b>{s.name}</b>
              <span>{s.duty}</span>
            </div>
            {i < LOOP_STAGES.length - 1 ? (
              <span className="cyber-loop__sep">→</span>
            ) : null}
          </Fragment>
        ))}
        <span className="cyber-loop__sep">⟲</span>
      </div>

      {/* ② 逐轮流水：严格轮次升序，每轮一行关键指标 */}
      <div className="cyber-loop__rounds">
        {loops.map((l) => (
          <div key={l.round} className="cyber-loop__round">
            <button
              type="button"
              className="cyber-loop__roundhead"
              onClick={() => setOpenRound(openRound === l.round ? null : l.round)}
            >
              <span className="cyber-loop__roundno">第 {l.round} 轮</span>
              <span className="cyber-loop__who cyber-loop__who--red">
                红队 新增 {l.redNew} 步
              </span>
              <span className="cyber-loop__who cyber-loop__who--blue">
                蓝队 告警 {l.blueAlerts} · 处置 {l.blueTriaged}
              </span>
              <span
                className={`cyber-loop__who cyber-loop__who--purple${
                  l.purpleValid ? " is-ok" : ""
                }`}
              >
                {l.purpleValid
                  ? "紫队 判定 ✓ 链路成立"
                  : `紫队 缺口 ${l.purpleIssues}（步骤 ${l.gapStep} / 链路 ${l.gapChain}）· ${
                      l.purpleSeverity || "待修"
                    }`}
              </span>
              <span className="cyber-loop__link">
                {l.prevRound == null
                  ? "链路首轮：红队自主建链，蓝紫队建立基线"
                  : `承接第 ${l.prevRound} 轮缺口 · 已闭合 ${l.closed}/${l.prevIssues}`}
              </span>
              <span className="cyber-loop__caret">
                {openRound === l.round ? "收起 ▲" : "明细 ▼"}
              </span>
            </button>
            {l.redTechs.length || l.blueActions.length ? (
              <div className="cyber-loop__detail">
                {l.redTechs.length ? (
                  <>
                    <span className="cyber-loop__tag cyber-loop__tag--red">
                      红队技法
                    </span>
                    {l.redTechs.join(" / ")}
                  </>
                ) : null}
                {l.blueActions.length ? (
                  <>
                    <span className="cyber-loop__tag cyber-loop__tag--blue">
                      蓝队动作
                    </span>
                    {l.blueActions.join(" / ")}
                  </>
                ) : null}
              </div>
            ) : null}
            {openRound === l.round && l.issueTexts.length ? (
              <ul className="cyber-loop__issues">
                {l.issueTexts.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ))}
      </div>

      {/* ③ 收敛结论：缺口数变化 + 判定变化 + 闭环率 */}
      <p className="cyber-loop__summary">
        缺口数 {loops.map((l) => l.purpleIssues).join(" → ")} · 判定{" "}
        {loops.map((l) => (l.purpleValid ? "✓" : "✗")).join(" → ")} · 累计闭合{" "}
        {closedTotal}/{totalGaps} 条缺口；
        {last.purpleValid
          ? "末轮紫队判定通过，循环收敛终止"
          : `末轮仍未通过（${last.code || "未收敛"}），最后一批缺口转人工复核`}
      </p>
    </div>
  );
}


/** 最近一轮演练的浏览器快照（sessionStorage）：切 tab/刷新后仍可恢复展示，
 *  只有开启新一轮时才被清除/覆盖。 */
const DRILL_SNAPSHOT_KEY = "aegis.cyber-drill.snapshot";

// T8 战报导出：把运行记录 Markdown 排版成打印友好的 HTML，
// 新窗口打开并触发浏览器打印（可另存为 PDF / 直接打印）。
// 纯前端实现，零依赖；不引入后端生成 PDF 的成本。
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// T7 历史演练对比：迷你趋势图（metric: red=新增攻击步骤 / cov=防御覆盖率）
function CompareSpark({
  roundsA,
  roundsB,
  colorA,
  colorB,
  metric,
}: {
  roundsA: DrillRound[];
  roundsB: DrillRound[];
  colorA: string;
  colorB: string;
  metric: "red" | "cov";
}) {
  const W = 300;
  const H = 110;
  const PAD_L = 30;
  const PAD_R = 10;
  const PAD_T = 14;
  const PAD_B = 20;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const toPoints = (rounds: DrillRound[]) =>
    rounds.map((r) => ({
      round: r.round,
      val: metric === "red" ? (r.red.new_steps ?? []).length : (roundCoverage(r) ?? 0),
    }));

  const pa = toPoints(roundsA);
  const pb = toPoints(roundsB);
  const maxRounds = Math.max(pa.length, pb.length, 1);
  const maxVal =
    metric === "cov"
      ? 100
      : Math.max(1, ...pa.map((p) => p.val), ...pb.map((p) => p.val));
  const x = (i: number) =>
    PAD_L + (maxRounds === 1 ? plotW / 2 : (i / (maxRounds - 1)) * plotW);
  const y = (v: number, max: number) =>
    PAD_T + plotH - (v / max) * plotH;

  const line = (pts: { round: number; val: number }[], max: number) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.val, max)}`).join(" ");

  return (
    <svg className="cyber-compare__svg" viewBox={`0 0 ${W} ${H}`}>
      {[0, 0.5, 1].map((t) => (
        <line
          key={t}
          x1={PAD_L}
          x2={W - PAD_R}
          y1={PAD_T + plotH * t}
          y2={PAD_T + plotH * t}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="1"
        />
      ))}
      {pa.length > 1 ? (
        <path d={line(pa, maxVal)} fill="none" stroke={colorA} strokeWidth="2" />
      ) : null}
      {pb.length > 1 ? (
        <path d={line(pb, maxVal)} fill="none" stroke={colorB} strokeWidth="2" />
      ) : null}
      {pa.map((p, i) => (
        <circle key={`a${i}`} cx={x(i)} cy={y(p.val, maxVal)} r="2.5" fill={colorA} />
      ))}
      {pb.map((p, i) => (
        <circle key={`b${i}`} cx={x(i)} cy={y(p.val, maxVal)} r="2.5" fill={colorB} />
      ))}
      <text x={PAD_L} y={PAD_T - 4} fill="var(--text-dim)" fontSize="9">
        {metric === "red" ? "新增攻击步骤" : "防御覆盖率 %"}
      </text>
      <text x={W - PAD_R} y={H - 6} fill="var(--text-dim)" fontSize="9" textAnchor="end">
        round
      </text>
    </svg>
  );
}

// T7 历史演练对比区：列出本地持久化的演练，勾选两个并排对比。
function HistoryDrills({
  current,
  onLoad,
}: {
  current: DrillRecord | null;
  onLoad: (id: string) => void;
}) {
  const [drills, setDrills] = useState<DrillMeta[] | null>(null);
  const [sel, setSel] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    cyberApi
      .listDrills()
      .then((res) => setDrills(res.drills ?? []))
      .catch(() => setDrills([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = (id: string) => {
    setSel((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return prev;
      return [...prev, id];
    });
  };

  const pair = drills?.filter((d) => sel.includes(d.drill_id)) ?? [];

  return (
    <div className="cyber-history">
      <div className="cyber-history__head">
        <h4 className="cyber-panel__subtitle">🕘 历史演练</h4>
        <button
          type="button"
          className="cyber-view__btn cyber-view__btn--ghost"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? "刷新中…" : "↻ 刷新"}
        </button>
      </div>
      {drills && drills.length > 0 ? (
        <>
          <p className="cyber-history__hint">
            勾选两个演练对比收敛过程（当前会话中的演练会自动列入）
          </p>
          <div className="cyber-history__list">
            {drills.map((d) => {
              const isCurrent = current?.drill_id === d.drill_id;
              const checked = sel.includes(d.drill_id);
              return (
                <label
                  key={d.drill_id}
                  className={`cyber-history__item${checked ? " is-checked" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(d.drill_id)}
                  />
                  <span className="cyber-history__item-id">
                    {d.drill_id}
                    {isCurrent ? (
                      <span className="cyber-history__current">当前</span>
                    ) : null}
                  </span>
                  <span className="cyber-history__item-meta">
                    {d.target_range} · {d.rounds_executed} 轮 ·{" "}
                    <code>{d.convergence_code}</code>
                  </span>
                  <span className="cyber-history__item-time">
                    {d.created_at ? d.created_at.slice(0, 16).replace("T", " ") : ""}
                  </span>
                </label>
              );
            })}
          </div>
          {pair.length === 2 ? (
            <CompareView a={pair[0]} b={pair[1]} />
          ) : null}
          <div className="cyber-history__load">
            {pair.length === 1 ? (
              <button
                type="button"
                className="cyber-view__btn"
                onClick={() => onLoad(pair[0].drill_id)}
              >
                加载到当前面板
              </button>
            ) : null}
          </div>
        </>
      ) : (
        <p className="cyber-panel__empty">
          {loading ? "加载中…" : "暂无历史演练记录 —— 先跑一次演练（mock 秒回）"}
        </p>
      )}
    </div>
  );
}

// T7 对比视图：拉取两个完整记录 → 指标对比表 + 新增步骤/覆盖率双迷你趋势图
function CompareView({ a, b }: { a: DrillMeta; b: DrillMeta }) {
  const [recs, setRecs] = useState<Record<string, DrillRecord>>({});
  const key = `${a.drill_id}|${b.drill_id}`;

  useEffect(() => {
    let cancelled = false;
    setRecs({});
    Promise.all([cyberApi.getDrill(a.drill_id), cyberApi.getDrill(b.drill_id)])
      .then(([ra, rb]) => {
        if (cancelled) return;
        setRecs({ [ra.drill_id]: ra, [rb.drill_id]: rb });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [key, a.drill_id, b.drill_id]);

  const ra = recs[a.drill_id];
  const rb = recs[b.drill_id];

  return (
    <div className="cyber-compare">
      <div className="cyber-compare__table">
        <table>
          <thead>
            <tr>
              <th>指标</th>
              <th style={{ color: "#e05252" }}>演练 A · {a.drill_id}</th>
              <th style={{ color: "#2f7de1" }}>演练 B · {b.drill_id}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>目标网络</td>
              <td>{a.target_range}</td>
              <td>{b.target_range}</td>
            </tr>
            <tr>
              <td>实际轮次</td>
              <td>{a.rounds_executed}</td>
              <td>{b.rounds_executed}</td>
            </tr>
            <tr>
              <td>收敛码</td>
              <td><code>{a.convergence_code}</code></td>
              <td><code>{b.convergence_code}</code></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="cyber-compare__row">
        <div className="cyber-compare__chart">
          <div className="cyber-compare__legend">
            <i style={{ background: "#e05252" }} /> A · {a.drill_id}
            <i style={{ background: "#2f7de1", marginLeft: 8 }} /> B · {b.drill_id}
          </div>
          <CompareSpark
            roundsA={ra?.rounds ?? []}
            roundsB={rb?.rounds ?? []}
            colorA="#e05252"
            colorB="#2f7de1"
            metric="red"
          />
        </div>
        <div className="cyber-compare__chart">
          <div className="cyber-compare__legend">
            <i style={{ background: "#2e9e5b" }} /> 覆盖率 %（A 红 / B 蓝）
          </div>
          <CompareSpark
            roundsA={ra?.rounds ?? []}
            roundsB={rb?.rounds ?? []}
            colorA="#e05252"
            colorB="#2f7de1"
            metric="cov"
          />
        </div>
      </div>
    </div>
  );
}

function exportReportPdf(reportMd: string, drillId: string | null): void {
  // R18d：改为下载真正的 PDF 文件（调用后端 /report.pdf，reportlab 渲染中文），
  // 替代原先的 window.open + win.print()（那会弹出打印对话框而非下载 PDF）。
  void (async () => {
    if (!drillId) return;
    try {
      const blob = await cyberApi.getDrillReportPdf(drillId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aegis-drill-${drillId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("导出 PDF 失败，回退到打印预览", err);
      // 回退：若后端不可用，退回原 print 预览（不静默失败）
      _printFallback(reportMd, drillId);
    }
  })();
}

/** 后端 PDF 不可用时的打印预览回退（保留原行为，避免导出彻底失效）。 */
function _printFallback(reportMd: string, drillId: string | null): void {
  const lines = reportMd.split("\n");
  const html = lines
    .map((raw) => {
      const line = raw.replace(/\r$/, "");
      const esc = (t: string) => escapeHtml(t);
      const h = line.match(/^(#{1,4})\s+(.*)$/);
      if (h) return `<h${h[1].length}>${esc(h[2])}</h${h[1].length}>`;
      if (/^\s*[-*]\s+/.test(line)) return `<li>${esc(line)}</li>`;
      if (/^\s*\|.*\|\s*$/.test(line)) {
        if (/^\s*\|[\s:|-]+\|\s*$/.test(line)) return "";
        const cells = line
          .split("|")
          .slice(1, -1)
          .map((c) => `<td>${esc(c.trim())}</td>`)
          .join("");
        return `<tr>${cells}</tr>`;
      }
      if (/^\s*```/.test(line)) return "";
      return `<p>${esc(line) || "&nbsp;"}</p>`;
    })
    .join("\n");
  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) return;
  win.document.write(`<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>AegisOS 演练战报 ${drillId ?? ""}</title>
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; margin: 32px; color: #1a2233; }
  h1 { font-size: 22px; border-bottom: 2px solid #2f7de1; padding-bottom: 8px; }
  h2 { font-size: 17px; border-left: 4px solid #2f7de1; padding-left: 8px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  td { border: 1px solid #ccc; padding: 4px 8px; font-size: 12px; }
</style>
</head>
<body>
<h1>AegisOS 攻防演练运行记录${drillId ? ` · ${escapeHtml(drillId)}` : ""}</h1>
${html}
</body>
</html>`);
  win.document.close();
  win.focus();
  win.print();
}

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

      {/* T5 紫队缺口闭环：反馈驱动演化证据链 */}
      {rounds.length >= 2 ? <GapClosureChart rounds={rounds} /> : null}

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
                            const techId = (t: any) => {
                              const m = /^(T\d+(?:\.\d+)?)/.exec(String(t));
                              return m ? m[1] : t;
                            };
                            const atk = [
                              ...new Set(
                                (round.red.steps as any[])
                                  .map((s) => s.technique)
                                  .filter(Boolean)
                                  .map(techId),
                              ),
                            ];
                            const det = [
                              ...new Set(
                                (round.blue.alerts as any[])
                                  .map((a) => a.technique)
                                  .filter(Boolean)
                                  .map(techId),
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
                <button
                  type="button"
                  className="cyber-view__btn cyber-view__btn--primary"
                  onClick={() => exportReportPdf(reportMd, drillId)}
                >
                  🖨 导出 PDF
                </button>
              ) : null}
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

      {/* T7 历史演练对比：本地持久化记录列表 + 双演练对比 */}
      <HistoryDrills
        current={
          drillId && rounds.length > 0
            ? {
                drill_id: drillId,
                target_range: targetRange,
                max_rounds: maxRounds,
                rounds_executed: rounds.length,
                convergence_code: summary?.convergence_code ?? "running",
                rounds,
                summary: summary ?? { conclusion: "", convergence_code: "running", rounds_executed: rounds.length },
              }
            : null
        }
        onLoad={(id) => setDrillId(id)}
      />
    </div>
  );
}
