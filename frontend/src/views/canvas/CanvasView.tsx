// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 升级为本地任务 DAG 演示视图，支持依赖布局、状态筛选和节点详情

import { useEffect, useMemo, useState } from "react";
import { useAppStore } from "@/lib/store";
import type { Event, Task } from "@/protocol/types";
import { taskApi } from "@/services/api/tasks";

type Filter = "all" | "pending" | "running" | "succeeded" | "failed";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "pending", label: "待处理" },
  { value: "running", label: "执行中" },
  { value: "succeeded", label: "已完成" },
  { value: "failed", label: "失败" },
];

function taskId(task: Task, index: number): string {
  return task.task_id || `task-${index + 1}`;
}

function taskDepth(task: Task, tasks: Task[], seen = new Set<string>()): number {
  const id = task.task_id || "";
  if (!id || seen.has(id)) return 0;
  seen.add(id);
  const dependencies = task.dependency ?? [];
  return dependencies.reduce((depth, dependency) => {
    const parent = tasks.find((candidate) => candidate.task_id === dependency);
    return parent ? Math.max(depth, taskDepth(parent, tasks, new Set(seen)) + 1) : depth;
  }, 0);
}

function statusLabel(status: string): string {
  return { pending: "待处理", running: "执行中", succeeded: "已完成", failed: "失败", cancelled: "已取消" }[status] || status;
}

function phaseMeta(stage: number): { label: string; tone: string } {
  if (stage <= 4) return { label: "红队", tone: "red" };
  if (stage <= 8) return { label: "蓝队", tone: "blue" };
  return { label: "紫队", tone: "purple" };
}

function compact(value: unknown, limit = 120): string {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function taskOutput(task: Task): unknown {
  return task.result?.output ?? task.result;
}

function outputEntries(value: unknown): Array<[string, string]> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [["结果", compact(value)]];
  return Object.entries(value as Record<string, unknown>).map(([key, entry]) => [key, compact(entry, 260)]);
}

function taskEvents(task: Task, events: Event[]) {
  return events.filter((event) => event.task_id === task.task_id || event.payload?.task_id === task.task_id);
}

export function CanvasView() {
  const tasks = useAppStore((s) => s.tasks);
  const events = useAppStore((s) => s.events);
  const chatMessages = useAppStore((s) => s.chatMessages);
  const setTasks = useAppStore((s) => s.setTasks);
  const currentSession = useAppStore((s) => s.currentSession);
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const sessionId = currentSession?.id;
    if (sessionId) void taskApi.list(sessionId).then((remoteTasks) => {
      const localDrillTasks = useAppStore.getState().tasks.filter((task) => task.payload?.source === "chat-drill");
      for (let index = 0; index < sessionStorage.length; index += 1) {
        const key = sessionStorage.key(index);
        if (!key?.startsWith("aegis.canvas.drill.")) continue;
        try {
          const saved = JSON.parse(sessionStorage.getItem(key) ?? "[]") as Task[];
          localDrillTasks.push(...saved);
        } catch { /* 忽略损坏的旧快照 */ }
      }
      const merged = new Map<string, Task>();
      [...remoteTasks, ...localDrillTasks].forEach((task) => {
        if (task.task_id) merged.set(task.task_id, task);
      });
      setTasks([...merged.values()]);
    }).catch(() => {});
  }, [currentSession?.id, setTasks]);

  const visibleTasks = useMemo(
    () => tasks.filter((task) => filter === "all" || task.status === filter),
    [filter, tasks],
  );
  const runningTasks = tasks.filter((task) => task.status === "running");
  const completedTasks = tasks.filter((task) => task.status === "succeeded");
  const failedTasks = tasks.filter((task) => task.status === "failed");
  const recentTasks = [...tasks]
    .sort((left, right) => String(right.task_id ?? "").localeCompare(String(left.task_id ?? "")))
    .slice(0, 5);
  const selectedTask = selectedId
    ? visibleTasks.find((task, index) => taskId(task, index) === selectedId)
    : undefined;
  const selectedEvents = selectedTask ? taskEvents(selectedTask, events) : [];
  const selectedMessages = selectedTask ? chatMessages.filter((message) => message.taskId === selectedTask.task_id) : [];
  const columns = useMemo(() => {
    const grouped = new Map<number, Task[]>();
    visibleTasks.forEach((task) => {
      const depth = taskDepth(task, visibleTasks);
      grouped.set(depth, [...(grouped.get(depth) ?? []), task]);
    });
    return [...grouped.entries()].sort(([left], [right]) => left - right);
  }, [visibleTasks]);

  useEffect(() => {
    if (!selectedId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedId]);

  const loadDemoFlow = async () => {
    const sessionId = useAppStore.getState().currentSession?.id;
    if (!sessionId) return;
    let previous = "";
    const stages = [
      "侦察目标资产",
      "关联 CVE 漏洞",
      "规划初始访问",
      "横向移动路径",
      "检测入侵事件",
      "告警分诊排序",
      "威胁狩猎假设",
      "制定响应计划",
      "紫队一致性审查",
    ];
    for (const [index, goal] of stages.entries()) {
      const task = await taskApi.create({
        goal,
        session_id: sessionId,
        dependency: previous ? [previous] : [],
        priority: stages.length - index,
        payload: { demo_flow: true, stage: index + 1 },
      });
      previous = task.task_id ?? previous;
    }
    setTasks(await taskApi.list(sessionId));
  };

  return (
    <section className="view canvas-view">
      <header className="view__header">
        <div className="canvas-heading-row">
          <div>
            <span className="eyebrow">实时执行 / 任务协作</span>
            <h2 className="view__title">任务画布</h2>
          </div>
          <span className={`canvas-live-indicator${runningTasks.length ? " canvas-live-indicator--active" : ""}`}>
            <i /> {runningTasks.length ? "执行中" : "待命"}
          </span>
        </div>
        <p className="view__desc">
          先看执行中的 Agent，再回看任务如何沿依赖关系推进。
        </p>
      </header>

      <div className="canvas-overview" aria-label="执行概览">
        <div className="canvas-overview__lead"><span>当前队列</span><strong>{tasks.length}</strong><small>个后端任务</small></div>
        <div><span>执行中</span><strong>{runningTasks.length}</strong><small>Agent 正在处理</small></div>
        <div><span>已完成</span><strong>{completedTasks.length}</strong><small>已有产出</small></div>
        <div><span>需关注</span><strong>{failedTasks.length}</strong><small>失败或需复核</small></div>
      </div>

      {tasks.length > 0 ? <section className="canvas-activity-strip" aria-label="最近活动">
        <div className="canvas-activity-strip__heading"><span>最近活动</span><small>{events.length} 条实时事件</small></div>
        <div className="canvas-activity-strip__items">
          {recentTasks.map((task) => {
            const activity = taskEvents(task, events);
            const agent = String(task.payload?.agent_id ?? task.payload?.agent ?? activity[0]?.source?.node_id ?? task.result?.agent_id ?? "待分配");
            return <button type="button" key={task.task_id} className="canvas-activity-item" onClick={() => setSelectedId(task.task_id ?? null)}>
              <span className={`canvas-activity-item__dot canvas-activity-item__dot--${task.status ?? "pending"}`} />
              <span><b>{agent}</b><strong>{task.goal || task.task_id}</strong></span>
              <em>{statusLabel(task.status ?? "pending")} · 查看详情</em>
            </button>;
          })}
        </div>
      </section> : null}

      <div className="canvas-toolbar" role="toolbar" aria-label="任务筛选">
        <div className="canvas-toolbar__intro">
          <span className="canvas-toolbar__label">任务状态</span>
          <span className="canvas-toolbar__count"><span>当前显示</span><strong>{visibleTasks.length} 个任务</strong></span>
        </div>
        <div className="canvas-toolbar__filters" aria-label="任务状态选项">
          {FILTERS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`canvas-filter${filter === option.value ? " canvas-filter--active" : ""}`}
              onClick={() => setFilter(option.value)}
              aria-pressed={filter === option.value}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {visibleTasks.length === 0 ? (
        <div className="view__body view__empty">
          <p className="view__empty-text">还没有可展示的任务。先从 Chat 创建一个目标。</p>
          <button type="button" className="canvas-demo-cta" onClick={() => void loadDemoFlow()}>
            创建后端攻防流程
          </button>
        </div>
      ) : (
        <div className="canvas-layout">
          <div className="canvas-board" aria-label="任务依赖图">
            <div className="canvas-board__axis">真实任务依赖流向</div>
            <div className="canvas-swimlanes">
              {(["red", "blue", "purple"] as const).map((tone) => {
                const phaseColumns = columns.filter(([depth, tasksInColumn]) => tasksInColumn.some((task) => {
                  const taskPhase = task.payload?.phase;
                  return taskPhase ? taskPhase === tone : phaseMeta(depth + 1).tone === tone;
                }));
                if (!phaseColumns.length) return null;
                const phaseLabel = tone === "red" ? "红队 · 攻击面建立" : tone === "blue" ? "蓝队 · 检测与响应" : "紫队 · 对抗校验";
                return (
                  <section className={`canvas-swimlane canvas-swimlane--${tone}`} key={tone}>
                    <header className="canvas-swimlane__header">
                      <span className="canvas-swimlane__mark" />
                      <strong>{phaseLabel}</strong>
                      <small>{phaseColumns.reduce((total, [, tasksInColumn]) => total + tasksInColumn.length, 0)} 个阶段</small>
                    </header>
                    <div className="canvas-board__columns">
                      {phaseColumns.map(([depth, column]) => (
                        <div className="canvas-column" key={depth}>
                          <span className="canvas-column__label">阶段 {depth + 1}</span>
                          {column.filter((task) => {
                            const taskPhase = task.payload?.phase;
                            return taskPhase ? taskPhase === tone : phaseMeta(Number(task.payload?.stage ?? depth + 1)).tone === tone;
                          }).map((task, index) => {
                            const id = taskId(task, index);
                            const status = task.status || "pending";
                            const stage = Number(task.payload?.stage ?? depth + 1);
                            const phase = task.payload?.phase
                              ? { label: task.payload.phase === "red" ? "红队" : task.payload.phase === "blue" ? "蓝队" : "紫队", tone: String(task.payload.phase) }
                              : phaseMeta(stage);
                            const activity = taskEvents(task, events);
                            const agent = String(task.payload?.agent_id ?? task.payload?.agent ?? activity[0]?.source?.node_id ?? task.result?.agent_id ?? "待分配");
                            return (
                              <button
                                type="button"
                                key={id}
                                className={`canvas-node canvas-node--${status} canvas-node--${phase.tone}${selectedTask && taskId(selectedTask, 0) === id ? " canvas-node--selected" : ""}`}
                                onClick={() => setSelectedId(id)}
                              >
                                <span className="canvas-node__signal" aria-hidden="true" />
                                <span className="canvas-node__body">
                                  <strong>{task.goal || id}</strong>
                                  <small>{phase.label} · {statusLabel(status)} · {agent}</small>
                                  <em className="canvas-node__open">查看协作详情</em>
                                </span>
                                <span className="canvas-node__priority">S{String(stage).padStart(2, "0")}</span>
                              </button>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </section>
                );
              })}
            </div>
            {columns.length > 1 ? (
              <div className="canvas-dependency-rail" aria-label="任务依赖连接">
                {visibleTasks.flatMap((task, index) =>
                  (task.dependency ?? []).map((dependency) => {
                    const child = taskId(task, index);
                    const parent = visibleTasks.find((candidate) => candidate.task_id === dependency);
                    return parent ? (
                      <span key={`${dependency}-${child}`}>
                        <code>{parent.goal || dependency.slice(0, 8)}</code> → <code>{task.goal || child.slice(0, 8)}</code>
                      </span>
                    ) : null;
                  }),
                )}
              </div>
            ) : null}
          </div>

          {selectedTask ? (
            <div className="canvas-modal" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedId(null); }}>
            <aside className="canvas-inspector" role="dialog" aria-modal="true" aria-label="任务详情">
              <button type="button" className="canvas-inspector__close" aria-label="关闭任务详情" onClick={() => setSelectedId(null)}>×</button>
              <span className="canvas-inspector__eyebrow">当前任务</span>
              <h3>{selectedTask.goal || selectedTask.task_id}</h3>
              <span className={`badge badge--${selectedTask.status ?? "pending"}`}>
                {statusLabel(selectedTask.status ?? "pending")}
              </span>
              <dl className="canvas-inspector__facts">
                <div><dt>任务 ID</dt><dd>{selectedTask.task_id || "未命名"}</dd></div>
                <div><dt>流程阶段</dt><dd>S{String(Number(selectedTask.payload?.stage ?? 1)).padStart(2, "0")}</dd></div>
                <div><dt>优先级</dt><dd>P{selectedTask.priority ?? 0}</dd></div>
                <div><dt>延迟预算</dt><dd>{selectedTask.latency_budget ?? 10}s</dd></div>
                <div><dt>依赖</dt><dd>{selectedTask.dependency?.length ? selectedTask.dependency.join(", ") : "无"}</dd></div>
              </dl>
              <section className="canvas-inspector__activity">
                <div className="canvas-inspector__section-heading"><h4>协作与产出</h4><span>{selectedEvents.length} 个事件</span></div>
                <div className="canvas-collaboration-grid">
                  <div className="canvas-collaboration-card canvas-collaboration-card--context"><span className="canvas-card-label">输入目标</span><strong>{selectedTask.goal || "未命名任务"}</strong><small>来自当前任务</small></div>
                  <div className="canvas-collaboration-card canvas-collaboration-card--agent"><span className="canvas-card-label">执行 Agent</span><strong>{String(selectedTask.payload?.agent_id ?? selectedTask.payload?.agent ?? selectedEvents[0]?.source?.node_id ?? selectedTask.result?.agent_id ?? "待分配")}</strong><small>{statusLabel(selectedTask.status ?? "pending")}</small></div>
                </div>
                <div className="canvas-output-panel">
                  <div className="canvas-output-panel__heading"><span>结构化产出</span><small>{selectedTask.result ? "已持久化" : "等待结果"}</small></div>
                  <dl>{outputEntries(taskOutput(selectedTask) || selectedEvents.find((event) => event.event_type === "agent.finish")?.payload?.output || selectedMessages.at(-1)?.content || selectedTask.plan || "等待 Agent 输出").map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
                </div>
                <div className="canvas-activity-list">
                  <div className="canvas-activity-list__heading">执行轨迹</div>
                  {selectedEvents.length ? selectedEvents.slice(-6).map((event) => <div key={event.event_id}><b>{event.event_type}</b><span>{event.source?.node_id || "system"}</span></div>) : <p>等待实时事件...</p>}
              </div>
              </section>
            </aside>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
