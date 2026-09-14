// date: 2026-09-14
// dev: OpenSquilla
// R21: Graph + Canvas 合并为「任务图 TaskMap」——同一画布承载两类数据流。
// R22: 布局重做（用户反馈 R21 节点挤成一团、边不可见）：
//   - Cyber 演练流 → 轮次泳道：每轮红→蓝→紫一行，跨轮曲线标注「携带上轮摘要」，
//     轮内边标注真实数据流（攻击事件流 / 告警+响应），泳道底色分隔；
//   - Chat 对话流 → 依赖分层 DAG，画布宽高按层数/节点数自适应扩展；
//   - 贝塞尔连线 + 箭头 + 流向标签，节点加 tier 徽标胶囊，右上角缩放控件；
//   - 点击节点 → 右侧检视面板（低代码风格，R21 保留）。

import { useEffect, useMemo, useState } from "react";
import { useAppStore } from "@/lib/store";
import { taskApi } from "@/services/api/tasks";
import { graphService } from "@/services/graph";
import { cyberApi } from "@/services/api/cyber";
import type { DrillMeta, DrillRecord, DrillRoundPhases, Event, Task } from "@/protocol/types";

type MapTone = "red" | "blue" | "purple" | "neutral" | "memory";

interface MapNode {
  id: string;
  label: string;
  sublabel: string;
  tone: MapTone;
  status: string;
  tier?: string;
  detail: {
    kind: string;
    agent?: string;
    input?: string;
    output?: string;
    extra?: Array<[string, string]>;
  };
}

interface MapEdge {
  src: string;
  dst: string;
  label?: string;
  /** memory = 跨轮记忆流（虚线紫色） */
  kind?: "flow" | "memory";
}

interface Pt {
  x: number;
  y: number;
}

const NODE_W = 196;
const NODE_H = 64;
const PAD = 44;
const COL_GAP = 128; // Chat 模式列间距（留边标签空间）
const ROW_GAP = 36; // Chat 模式行间距
const LANE_X_GAP = 132; // Cyber 模式轮内节点间距
const LANE_H = NODE_H + 104; // Cyber 模式泳道高度（含跨轮曲线空间）

const TONE_COLOR: Record<MapTone, string> = {
  red: "#ef7770",
  blue: "#5b8def",
  purple: "#a78bfa",
  neutral: "#64748b",
  memory: "#a855f7",
};

const TONE_LABEL: Record<MapTone, string> = {
  red: "红队",
  blue: "蓝队",
  purple: "紫队",
  neutral: "系统",
  memory: "记忆",
};

const TIER_STYLE: Record<string, { fg: string; bg: string }> = {
  device: { fg: "#4ade80", bg: "rgba(74,222,128,0.14)" },
  edge: { fg: "#38bdf8", bg: "rgba(56,189,248,0.14)" },
  cloud: { fg: "#e7b65c", bg: "rgba(231,182,92,0.16)" },
};

const SNAPSHOT_KEY = "aegis.cyber-drill.snapshot";

function statusLabel(status: string): string {
  return (
    {
      pending: "待处理",
      running: "执行中",
      succeeded: "已完成",
      failed: "失败",
      cancelled: "已取消",
      converged: "已收敛",
    } as Record<string, string>
  )[status] || status;
}

function compact(value: unknown, limit = 240): string {
  if (value == null) return "—";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

// ---- Chat 模式：任务 DAG（含 Chat 发起的演练任务，随对话实时更新） ----
function taskTone(task: Task): MapTone {
  const phase = task.payload?.phase as string | undefined;
  if (phase === "red" || phase === "blue" || phase === "purple") return phase;
  const stage = Number(task.payload?.stage ?? 0);
  if (stage >= 1 && stage <= 4) return "red";
  if (stage >= 5 && stage <= 8) return "blue";
  if (stage >= 9) return "purple";
  return "neutral";
}

function buildChatMap(tasks: Task[], events: Event[]): { nodes: MapNode[]; edges: MapEdge[] } {
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];
  const ids = new Set(tasks.map((t) => t.task_id).filter(Boolean));
  for (const task of tasks) {
    const id = task.task_id ?? "";
    if (!id) continue;
    const tone = taskTone(task);
    const agent = String(task.payload?.agent_id ?? task.payload?.agent ?? "router");
    const tier = String(task.payload?.tier ?? "");
    const activity = events.filter((e) => e.task_id === id || e.payload?.task_id === id);
    const finish = activity.find((e) => e.event_type === "agent.finish");
    const output = task.result?.output ?? task.result ?? finish?.payload?.output;
    nodes.push({
      id,
      label: String(task.goal ?? id),
      sublabel: `${TONE_LABEL[tone]} · ${statusLabel(task.status ?? "pending")}`,
      tone,
      status: task.status ?? "pending",
      tier: tier || undefined,
      detail: {
        kind: "任务",
        agent,
        input: String(task.goal ?? id),
        output: output ? compact(output) : "等待 Agent 输出…",
        extra: [
          ["任务 ID", id],
          ["优先级", `P${task.priority ?? 0}`],
          ["延迟预算", `${task.latency_budget ?? 10}s`],
          ["依赖", (task.dependency ?? []).join(", ") || "无"],
          ["事件", `${activity.length} 条`],
        ],
      },
    });
    for (const dep of task.dependency ?? []) {
      if (ids.has(dep)) edges.push({ src: dep, dst: id, kind: "flow" });
    }
  }
  return { nodes, edges };
}

// ---- Cyber 模式：轮次泳道（每轮红→蓝→紫，跨轮记忆曲线） ----
function stepLine(step: Record<string, any>): string {
  return `${step.step_id ?? "?"} ${step.technique ?? ""} → ${step.to_asset ?? "?"}${step.success ? "" : " ✗"}`;
}

function buildCyberMap(record: DrillRecord): { nodes: MapNode[]; edges: MapEdge[] } {
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];
  for (const round of record.rounds ?? []) {
    const r = round.round;
    const phase = round.phase ?? ({} as DrillRoundPhases);
    const redId = `r${r}-red`;
    const blueId = `r${r}-blue`;
    const purpleId = `r${r}-purple`;
    const redTrace = round.red.agent_trace ?? [];
    const blueTrace = round.blue.agent_trace ?? [];
    const purpleTrace = round.purple.agent_trace ?? [];
    nodes.push(
      {
        id: redId,
        label: `红队 · 第 ${r} 轮`,
        sublabel: `${(round.red.steps ?? []).length} 步攻击 · ${round.red.finding_count ?? 0} 漏洞`,
        tone: "red",
        status: round.red.ok ? "succeeded" : "failed",
        tier: phase.red?.tier,
        detail: {
          kind: "红队",
          agent: phase.red?.model_id ?? "red-team",
          input: redTrace[0]?.input ?? "侦察目标网段，构建攻击链",
          output:
            (round.red.steps ?? []).map(stepLine).join("\n") ||
            compact(redTrace.at(-1)?.output) ||
            "无攻击步骤",
          extra: [
            ["资产", (round.red.assets ?? []).join(", ") || "—"],
            ["发现漏洞", `${round.red.finding_count ?? 0}`],
            ["执行落点", `${phase.red?.tier ?? "cloud"} · ${phase.red?.model_id ?? ""}`],
            ["路由理由", phase.red?.reason ?? "—"],
          ],
        },
      },
      {
        id: blueId,
        label: `蓝队 · 第 ${r} 轮`,
        sublabel: `${(round.blue.alerts ?? []).length} 告警 · ${(round.blue.plan?.actions ?? []).length ?? 0} 项处置`,
        tone: "blue",
        status: round.blue.ok ? "succeeded" : "failed",
        tier: phase.blue?.tier,
        detail: {
          kind: "蓝队",
          agent: phase.blue?.model_id ?? "blue-team",
          input: blueTrace[0]?.input ?? "接收红队攻击事件流，检测并响应",
          output: compact(round.blue.plan) || compact(blueTrace.at(-1)?.output) || "无响应计划",
          extra: [
            ["告警分诊", `${round.blue.triaged_count ?? 0} 条`],
            ["执行落点", `${phase.blue?.tier ?? "edge"} · ${phase.blue?.model_id ?? ""}`],
            ["路由理由", phase.blue?.reason ?? "—"],
          ],
        },
      },
      {
        id: purpleId,
        label: `紫队 · 第 ${r} 轮`,
        sublabel: `${round.purple.new_issue_count ?? 0} 缺口 · ${round.purple.valid ? "链路有效" : "待修正"}`,
        tone: "purple",
        status: round.purple.valid ? "succeeded" : "pending",
        tier: phase.purple?.tier,
        detail: {
          kind: "紫队",
          agent: phase.purple?.model_id ?? "purple-team",
          input: purpleTrace[0]?.input ?? "对红蓝对抗产物做一致性审查与收敛判定",
          output: compact(round.purple.critique) || compact(purpleTrace.at(-1)?.output) || "无审查意见",
          extra: [
            ["链路有效", round.purple.valid ? "是" : "否"],
            ["新增缺口", `${round.purple.new_issue_count ?? 0}`],
            ["执行落点", `${phase.purple?.tier ?? "cloud"} · ${phase.purple?.model_id ?? ""}`],
            ["路由理由", phase.purple?.reason ?? "—"],
          ],
        },
      },
    );
    edges.push(
      { src: redId, dst: blueId, label: "攻击事件流", kind: "flow" },
      { src: blueId, dst: purpleId, label: "告警+响应证据", kind: "flow" },
    );
    if (r > 1) {
      edges.push({ src: `r${r - 1}-purple`, dst: redId, label: "携带上轮摘要（跨轮记忆）", kind: "memory" });
    }
  }
  return { nodes, edges };
}

// ---- 布局：Chat 依赖分层 / Cyber 轮次泳道 ----
function chatLayout(nodes: MapNode[], edges: MapEdge[]): { pos: Map<string, Pt>; width: number; height: number } {
  const pos = new Map<string, Pt>();
  const ids = nodes.map((n) => n.id);
  if (!ids.length) return { pos, width: PAD * 2 + NODE_W, height: PAD * 2 + NODE_H };

  const depth = new Map<string, number>();
  const incoming = new Map<string, string[]>();
  for (const id of ids) incoming.set(id, []);
  for (const e of edges) {
    if (ids.includes(e.dst) && ids.includes(e.src)) incoming.get(e.dst)!.push(e.src);
  }
  const queue = ids.filter((id) => (incoming.get(id) ?? []).length === 0);
  for (const id of queue) depth.set(id, 0);
  const visited = new Set(queue);
  while (queue.length) {
    const cur = queue.shift()!;
    const d = depth.get(cur) ?? 0;
    for (const e of edges) {
      if (e.src !== cur || !ids.includes(e.dst)) continue;
      if (!visited.has(e.dst)) {
        visited.add(e.dst);
        depth.set(e.dst, d + 1);
        queue.push(e.dst);
      } else {
        depth.set(e.dst, Math.max(depth.get(e.dst) ?? 0, d + 1));
      }
    }
  }
  for (const id of ids) if (!depth.has(id)) depth.set(id, 0);

  const columns = new Map<number, string[]>();
  for (const id of ids) {
    const d = depth.get(id) ?? 0;
    columns.set(d, [...(columns.get(d) ?? []), id]);
  }
  const maxDepth = Math.max(...columns.keys(), 0);
  const maxRows = Math.max(...[...columns.values()].map((c) => c.length), 1);
  const width = PAD * 2 + maxDepth * (NODE_W + COL_GAP) + NODE_W;
  const height = PAD * 2 + (maxRows - 1) * (NODE_H + ROW_GAP) + NODE_H;
  for (const [d, members] of columns) {
    const x = PAD + NODE_W / 2 + d * (NODE_W + COL_GAP);
    const colH = members.length * NODE_H + (members.length - 1) * ROW_GAP;
    const startY = (height - colH) / 2 + NODE_H / 2;
    members.forEach((id, i) => pos.set(id, { x, y: startY + i * (NODE_H + ROW_GAP) }));
  }
  return { pos, width, height };
}

function cyberLayout(roundCount: number): { pos: Map<string, Pt>; width: number; height: number; lanes: Array<{ y: number; round: number }> } {
  const pos = new Map<string, Pt>();
  const lanes: Array<{ y: number; round: number }> = [];
  const n = Math.max(roundCount, 1);
  const width = PAD * 2 + 3 * NODE_W + 2 * LANE_X_GAP;
  const height = PAD * 2 + (n - 1) * LANE_H + NODE_H;
  for (let i = 0; i < roundCount; i += 1) {
    const r = i + 1;
    const y = PAD + NODE_H / 2 + i * LANE_H;
    lanes.push({ y, round: r });
    pos.set(`r${r}-red`, { x: PAD + NODE_W / 2, y });
    pos.set(`r${r}-blue`, { x: PAD + NODE_W + LANE_X_GAP + NODE_W / 2, y });
    pos.set(`r${r}-purple`, { x: PAD + 2 * (NODE_W + LANE_X_GAP) + NODE_W / 2, y });
  }
  return { pos, width, height, lanes };
}

/** 连线几何：同层水平贝塞尔；跨轮回绕（源底部 → 目标顶部）。 */
function edgeGeometry(a: Pt, b: Pt): { d: string; lx: number; ly: number } {
  if (b.x > a.x + NODE_W * 0.4) {
    const x1 = a.x + NODE_W / 2;
    const x2 = b.x - NODE_W / 2 - 7;
    const mx = (x1 + x2) / 2;
    return {
      d: `M ${x1} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${x2} ${b.y}`,
      lx: mx,
      ly: (a.y + b.y) / 2 - 8,
    };
  }
  const y1 = a.y + NODE_H / 2;
  const y2 = b.y - NODE_H / 2 - 7;
  const my = (y1 + y2) / 2;
  return {
    d: `M ${a.x} ${y1} C ${a.x} ${my}, ${b.x} ${my}, ${b.x} ${y2}`,
    lx: (a.x + b.x) / 2,
    ly: my - 6,
  };
}

export function TaskMapView() {
  const mode = useAppStore((s) => s.taskMapMode);
  const setMode = useAppStore((s) => s.setTaskMapMode);
  const tasks = useAppStore((s) => s.tasks);
  const events = useAppStore((s) => s.events);
  const chatMessages = useAppStore((s) => s.chatMessages);
  const setTasks = useAppStore((s) => s.setTasks);

  const [record, setRecord] = useState<DrillRecord | null>(null);
  const [drillId, setDrillId] = useState<string | null>(() => {
    const k = useAppStore.getState().taskMapSelectedNode;
    return k && k.startsWith("drill-") ? k : null;
  });
  const [drillMeta, setDrillMeta] = useState<DrillMeta[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 消费「演练历史 → 在任务图中查看」跳转参数
  useEffect(() => {
    const k = useAppStore.getState().taskMapSelectedNode;
    if (k && k.startsWith("drill-")) {
      setDrillId(k);
      useAppStore.getState().setTaskMapSelectedNode(null);
    }
  }, []);

  // Chat 模式：随任务刷新（5s 轮询 + store 实时推送），保留 Chat 发起的演练任务快照
  useEffect(() => {
    if (mode !== "chat") return;
    const refresh = () => {
      const sessionId = useAppStore.getState().currentSession?.id;
      if (sessionId) {
        void taskApi
          .list(sessionId)
          .then((remote) => {
            const store = useAppStore.getState();
            const localDrill = store.tasks.filter((t) => t.payload?.source === "chat-drill");
            for (let index = 0; index < sessionStorage.length; index += 1) {
              const key = sessionStorage.key(index);
              if (!key?.startsWith("aegis.taskmap.drill.") && !key?.startsWith("aegis.canvas.drill.")) continue;
              try {
                const saved = JSON.parse(sessionStorage.getItem(key) ?? "[]") as Task[];
                localDrill.push(...saved);
              } catch {
                /* 忽略损坏的旧快照 */
              }
            }
            const merged = new Map<string, Task>();
            [...remote, ...localDrill].forEach((t) => {
              if (t.task_id) merged.set(t.task_id, t);
            });
            setTasks([...merged.values()]);
          })
          .catch(() => {});
      }
      void graphService.fetch().catch(() => {});
    };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [mode, setTasks]);

  // Cyber 模式：跟随现场快照 / 指定历史演练（新一轮整体替换，不堆叠）
  useEffect(() => {
    if (mode !== "cyber") return;
    let cancelled = false;
    void cyberApi
      .listDrills()
      .then((resp) => {
        if (!cancelled) setDrillMeta(resp.drills ?? []);
      })
      .catch(() => {});

    const load = (id: string) => {
      void cyberApi
        .getDrill(id)
        .then((rec) => {
          if (cancelled) return;
          setRecord(rec);
          setError(null);
        })
        .catch(() => {
          if (!cancelled) setError("演练记录加载失败，请稍后重试");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };

    if (drillId) {
      setLoading(true);
      load(drillId);
      const timer = window.setInterval(() => load(drillId), 4000);
      return () => {
        cancelled = true;
        window.clearInterval(timer);
      };
    }

    // 跟随现场：读 CyberDrillPanel 写入的快照，新演练开始即整体切换
    const follow = () => {
      try {
        const raw = sessionStorage.getItem(SNAPSHOT_KEY);
        if (!raw) return;
        const snap = JSON.parse(raw) as { drillId?: string | null };
        if (snap.drillId) load(snap.drillId);
      } catch {
        /* ignore */
      }
    };
    follow();
    const timer = window.setInterval(follow, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [mode, drillId]);

  const map = useMemo(() => {
    if (mode === "chat") return buildChatMap(tasks, events);
    if (record) return buildCyberMap(record);
    return { nodes: [] as MapNode[], edges: [] as MapEdge[] };
  }, [mode, tasks, events, record]);

  const layout = useMemo(() => {
    if (mode === "cyber" && record) return cyberLayout((record.rounds ?? []).length);
    return chatLayout(map.nodes, map.edges);
  }, [mode, record, map]);

  const activeId =
    selectedNode && map.nodes.some((n) => n.id === selectedNode)
      ? selectedNode
      : mode === "cyber" && record
        ? `r${record.rounds?.[record.rounds.length - 1]?.round ?? 1}-purple`
        : map.nodes[0]?.id ?? null;
  const activeNode = map.nodes.find((n) => n.id === activeId) ?? null;

  const recentChat = useMemo(() => chatMessages.slice(-8), [chatMessages]);
  const liveDrillId = drillId ?? record?.drill_id ?? null;

  const zoom = (delta: number) => setScale((s) => Math.min(1.6, Math.max(0.5, +(s + delta).toFixed(2))));

  return (
    <section className="view taskmap-view">
      <header className="view__header">
        <div className="taskmap-heading-row">
          <div>
            <span className="eyebrow">统一协作视图 / 低代码检视</span>
            <h2 className="view__title">任务图</h2>
          </div>
          <div className="taskmap-mode-switch" role="tablist" aria-label="任务图模式">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "chat"}
              className={`taskmap-mode-switch__btn${mode === "chat" ? " is-active" : ""}`}
              onClick={() => setMode("chat")}
            >
              Chat 对话流
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "cyber"}
              className={`taskmap-mode-switch__btn${mode === "cyber" ? " is-active" : ""}`}
              onClick={() => setMode("cyber")}
            >
              Cyber Defense 演练流
            </button>
          </div>
        </div>
        <p className="view__desc">
          {mode === "chat"
            ? "对话任务流：按依赖分层展示任务 DAG，点击节点查看执行 Agent 的输入/输出；对话记忆保留在底部。"
            : "攻防演练流：每轮红→蓝→紫一条泳道，紫色虚线为跨轮记忆传递；随新一轮演练整体刷新，可回看历史。"}
        </p>
      </header>

      <div className="view__body">
        {mode === "cyber" ? (
          <div className="taskmap-toolbar">
            <label className="taskmap-toolbar__label" htmlFor="taskmap-history">
              历史演练
            </label>
            <select
              id="taskmap-history"
              className="taskmap-toolbar__select"
              value={drillId ?? ""}
              onChange={(event) => {
                setDrillId(event.target.value || null);
                setSelectedNode(null);
              }}
              disabled={loading}
            >
              <option value="">— 跟随当前演练 —</option>
              {drillMeta.map((drill) => (
                <option key={drill.drill_id} value={drill.drill_id}>
                  {drill.drill_id} · {drill.rounds_executed} 轮 · {drill.convergence_code}
                </option>
              ))}
            </select>
            {liveDrillId ? (
              <span className="taskmap-live">
                <i />
                {liveDrillId}
              </span>
            ) : null}
            <div className="taskmap-zoom" aria-label="画布缩放">
              <button type="button" onClick={() => zoom(-0.15)} aria-label="缩小">−</button>
              <span>{Math.round(scale * 100)}%</span>
              <button type="button" onClick={() => zoom(0.15)} aria-label="放大">＋</button>
              <button type="button" className="taskmap-zoom__reset" onClick={() => setScale(1)}>
                重置
              </button>
            </div>
          </div>
        ) : null}

        {error ? <div className="taskmap-error">{error}</div> : null}

        {map.nodes.length === 0 ? (
          <div className="view__empty">
            <p className="view__empty-text">
              {mode === "chat"
                ? "还没有可展示的任务节点。先从 Chat 发起一个目标，或发起一场攻防演练。"
                : "暂无演练数据。去 Cyber Defense 开始自动演练，或从上方历史下拉选择一场演练回看。"}
            </p>
          </div>
        ) : (
          <div className="taskmap-layout">
            <div className="taskmap-canvas" aria-label="任务图">
              <div className="taskmap-scroll">
                <svg
                  className="taskmap-svg"
                  width={layout.width * scale}
                  height={layout.height * scale}
                  viewBox={`0 0 ${layout.width} ${layout.height}`}
                  role="img"
                >
                  <defs>
                    <marker id="taskmap-arrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#7c93a5" />
                    </marker>
                    <marker id="taskmap-arrow-memory" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#a78bfa" />
                    </marker>
                    <marker id="taskmap-arrow-active" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#56c7a7" />
                    </marker>
                  </defs>

                  {/* Cyber：泳道底色带 + 轮次标签 */}
                  {mode === "cyber" && "lanes" in layout
                    ? (layout as { lanes: Array<{ y: number; round: number }> }).lanes.map((lane) => (
                        <g key={`lane-${lane.round}`}>
                          <rect
                            className="taskmap-lane-band"
                            x={16}
                            y={lane.y - NODE_H / 2 - 14}
                            width={layout.width - 32}
                            height={NODE_H + 28}
                            rx={10}
                          />
                          <text className="taskmap-lane-tag" x={26} y={lane.y - NODE_H / 2 - 2}>
                            第 {lane.round} 轮
                          </text>
                        </g>
                      ))
                    : null}

                  {/* 连线（贝塞尔 + 箭头 + 流向标签） */}
                  {map.edges.map((edge, index) => {
                    const a = layout.pos.get(edge.src);
                    const b = layout.pos.get(edge.dst);
                    if (!a || !b) return null;
                    const active = activeId === edge.src || activeId === edge.dst;
                    const geo = edgeGeometry(a, b);
                    const memory = edge.kind === "memory";
                    return (
                      <g key={`${edge.src}-${edge.dst}-${index}`}>
                        <path
                          d={geo.d}
                          fill="none"
                          stroke={active ? "#56c7a7" : memory ? "#a78bfa" : "#55707f"}
                          strokeWidth={active ? 2.2 : 1.6}
                          strokeDasharray={memory ? "6 5" : undefined}
                          markerEnd={`url(#${active ? "taskmap-arrow-active" : memory ? "taskmap-arrow-memory" : "taskmap-arrow"})`}
                          opacity={active ? 1 : 0.75}
                        />
                        {edge.label && scale >= 0.8 ? (
                          <text className={`taskmap-edge-label${memory ? " taskmap-edge-label--memory" : ""}`} x={geo.lx} y={geo.ly} textAnchor="middle">
                            {edge.label}
                          </text>
                        ) : null}
                      </g>
                    );
                  })}

                  {/* 节点 */}
                  {map.nodes.map((node) => {
                    const p = layout.pos.get(node.id);
                    if (!p) return null;
                    const color = TONE_COLOR[node.tone];
                    const active = activeId === node.id;
                    const running = node.status === "running" || node.status === "active";
                    const tierStyle = node.tier ? TIER_STYLE[node.tier] : undefined;
                    return (
                      <g
                        key={node.id}
                        className={`taskmap-node${active ? " taskmap-node--selected" : ""}${running ? " taskmap-node--running" : ""}`}
                        onClick={() => setSelectedNode(node.id)}
                        style={{ cursor: "pointer" }}
                      >
                        <rect
                          x={p.x - NODE_W / 2}
                          y={p.y - NODE_H / 2}
                          width={NODE_W}
                          height={NODE_H}
                          rx={10}
                          fill="rgba(13, 20, 28, 0.96)"
                          stroke={active ? "#56c7a7" : color}
                          strokeWidth={active ? 2.4 : 1.4}
                        />
                        <circle cx={p.x - NODE_W / 2 + 14} cy={p.y - 12} r={4.5} fill={color} />
                        <text x={p.x - NODE_W / 2 + 26} y={p.y - 8} className="taskmap-node__label">
                          {truncate(node.label, 13)}
                        </text>
                        <text x={p.x - NODE_W / 2 + 14} y={p.y + 14} className="taskmap-node__sublabel">
                          {truncate(node.sublabel, 22)}
                        </text>
                        {node.tier ? (
                          <g>
                            <rect
                              x={p.x + NODE_W / 2 - 58}
                              y={p.y - NODE_H / 2 + 8}
                              width={48}
                              height={16}
                              rx={8}
                              fill={tierStyle?.bg ?? "rgba(100,116,139,0.2)"}
                            />
                            <text
                              x={p.x + NODE_W / 2 - 34}
                              y={p.y - NODE_H / 2 + 20}
                              textAnchor="middle"
                              className="taskmap-tier-pill"
                              fill={tierStyle?.fg ?? "#94a3b8"}
                            >
                              {node.tier}
                            </text>
                          </g>
                        ) : null}
                      </g>
                    );
                  })}
                </svg>
              </div>
              <div className="taskmap-legend">
                <span><i style={{ background: TONE_COLOR.red }} />红队</span>
                <span><i style={{ background: TONE_COLOR.blue }} />蓝队</span>
                <span><i style={{ background: TONE_COLOR.purple }} />紫队</span>
                <span><i style={{ background: TONE_COLOR.neutral }} />系统</span>
                <em>点击节点查看输入/输出 · 悬停连线看数据流</em>
              </div>
            </div>

            <aside className="taskmap-inspector" role="dialog" aria-modal="false" aria-label="节点输入输出">
              {activeNode ? (
                <>
                  <span className="taskmap-inspector__eyebrow">
                    {TONE_LABEL[activeNode.tone]} · {activeNode.detail.kind}
                  </span>
                  <h3>{activeNode.label}</h3>
                  <code>{activeNode.id}</code>
                  <span className={`badge badge--${activeNode.status}`}>{statusLabel(activeNode.status)}</span>
                  {activeNode.detail.agent ? (
                    <p className="taskmap-inspector__agent">执行 Agent：<b>{activeNode.detail.agent}</b></p>
                  ) : null}
                  {activeNode.tier ? (
                    <p className="taskmap-inspector__tier">
                      执行落点：
                      <b style={{ color: TIER_STYLE[activeNode.tier]?.fg ?? "#94a3b8" }}>{activeNode.tier}</b>
                    </p>
                  ) : null}
                  <section className="taskmap-inspector__io">
                    <div className="taskmap-io-card taskmap-io-card--input">
                      <span className="taskmap-io-card__tag">输入 INPUT</span>
                      <pre>{activeNode.detail.input ?? "—"}</pre>
                    </div>
                    <div className="taskmap-io-card taskmap-io-card--output">
                      <span className="taskmap-io-card__tag">输出 OUTPUT</span>
                      <pre>{activeNode.detail.output ?? "—"}</pre>
                    </div>
                  </section>
                  {activeNode.detail.extra?.length ? (
                    <dl className="taskmap-inspector__facts">
                      {activeNode.detail.extra.map(([key, value]) => (
                        <div key={key}>
                          <dt>{key}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}
                </>
              ) : (
                <p className="taskmap-inspector__empty">点击图上的节点查看输入/输出</p>
              )}
            </aside>
          </div>
        )}

        {/* Chat 模式：对话记忆条——对话是记忆的载体，随新问题持续追加 */}
        {mode === "chat" ? (
          <section className="taskmap-chat-strip" aria-label="对话记忆">
            <div className="taskmap-chat-strip__heading">
              <span>对话记忆（最近 {recentChat.length} 条）</span>
              <small>{chatMessages.length} 条总计 · 记忆面板见 Monitor</small>
            </div>
            <div className="taskmap-chat-strip__items">
              {recentChat.length === 0 ? (
                <p className="taskmap-chat-strip__empty">暂无对话，去 Chat 提问吧。</p>
              ) : (
                recentChat.map((message) => (
                  <div className={`taskmap-chat-item taskmap-chat-item--${message.role}`} key={message.id}>
                    <b>{message.role === "user" ? "用户" : message.role === "assistant" ? "Agent" : "系统"}</b>
                    <span>{compact(message.content, 140)}</span>
                  </div>
                ))
              )}
            </div>
          </section>
        ) : null}
      </div>
    </section>
  );
}
