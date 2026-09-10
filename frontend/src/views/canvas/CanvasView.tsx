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
    if (sessionId) void taskApi.list(sessionId).then(setTasks).catch(() => {});
  }, [currentSession?.id, setTasks]);

  const visibleTasks = useMemo(
    () => tasks.filter((task) => filter === "all" || task.status === filter),
    [filter, tasks],
  );
  const selectedTask = visibleTasks.find((task, index) => taskId(task, index) === selectedId) ?? visibleTasks[0];
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
        <h2 className="view__title">Task Canvas</h2>
        <p className="view__desc">
          用依赖关系观察任务如何从目标走向执行。
        </p>
      </header>

      <div className="canvas-toolbar" role="toolbar" aria-label="任务筛选">
        <span className="canvas-toolbar__label">任务状态</span>
        <div className="canvas-toolbar__filters">
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
        <span className="canvas-toolbar__count">{visibleTasks.length} 个任务</span>
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
                const phaseColumns = columns.filter(([depth]) => phaseMeta(depth + 1).tone === tone);
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
                          {column.map((task, index) => {
                            const id = taskId(task, index);
                            const status = task.status || "pending";
                            const stage = Number(task.payload?.stage ?? depth + 1);
                            const phase = phaseMeta(stage);
                            const activity = taskEvents(task, events);
                            const agent = String(task.payload?.agent_id ?? task.payload?.agent ?? activity[0]?.source?.node_id ?? task.result?.agent_id ?? "待分配");
                            const latestOutput = activity.find((event) => event.event_type === "agent.finish")?.payload?.output ?? taskOutput(task);
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
                                  {latestOutput ? <em className="canvas-node__output">↳ {compact(latestOutput, 48)}</em> : null}
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
            <aside className="canvas-inspector" aria-label="任务详情">
              <span className="canvas-inspector__eyebrow">SELECTED TASK</span>
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
                <h4>协作与产出</h4>
                <div className="canvas-output-block">
                  <span>输入目标</span>
                  <p>{compact(selectedTask.goal)}</p>
                </div>
                <div className="canvas-output-block">
                  <span>执行 Agent</span>
                  <p>{String(selectedTask.payload?.agent_id ?? selectedTask.payload?.agent ?? selectedEvents[0]?.source?.node_id ?? selectedTask.result?.agent_id ?? "待分配")}</p>
                </div>
                <div className="canvas-output-block">
                  <span>最新产出</span>
                  <p>{compact(taskOutput(selectedTask) || selectedEvents.find((event) => event.event_type === "agent.finish")?.payload?.output || selectedMessages.at(-1)?.content || selectedTask.plan || "等待 Agent 输出")}</p>
                </div>
                <div className="canvas-activity-list">
                  {selectedEvents.length ? selectedEvents.slice(-6).map((event) => (
                    <div key={event.event_id}>
                      <b>{event.event_type}</b><span>{event.source?.node_id || "system"}</span>
                    </div>
                  )) : <p>等待实时事件...</p>}
              </div>
              </section>
            </aside>
          ) : null}
        </div>
      )}
    </section>
  );
}
