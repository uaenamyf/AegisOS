// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 升级为本地任务 DAG 演示视图，支持依赖布局、状态筛选和节点详情

import { useMemo, useState } from "react";
import { useAppStore } from "@/lib/store";
import type { Task } from "@/protocol/types";

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

export function CanvasView() {
  const tasks = useAppStore((s) => s.tasks);
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const visibleTasks = useMemo(
    () => tasks.filter((task) => filter === "all" || task.status === filter),
    [filter, tasks],
  );
  const selectedTask = visibleTasks.find((task, index) => taskId(task, index) === selectedId) ?? visibleTasks[0];
  const columns = useMemo(() => {
    const grouped = new Map<number, Task[]>();
    visibleTasks.forEach((task) => {
      const depth = taskDepth(task, visibleTasks);
      grouped.set(depth, [...(grouped.get(depth) ?? []), task]);
    });
    return [...grouped.entries()].sort(([left], [right]) => left - right);
  }, [visibleTasks]);

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
        </div>
      ) : (
        <div className="canvas-layout">
          <div className="canvas-board" aria-label="任务依赖图">
            <div className="canvas-board__axis">依赖流向</div>
            <div className="canvas-board__columns">
              {columns.map(([depth, column]) => (
                <div className="canvas-column" key={depth}>
                  <span className="canvas-column__label">阶段 {depth + 1}</span>
                  {column.map((task, index) => {
                    const id = taskId(task, index);
                    const status = task.status || "pending";
                    return (
                      <button
                        type="button"
                        key={id}
                        className={`canvas-node canvas-node--${status}${selectedTask && taskId(selectedTask, 0) === id ? " canvas-node--selected" : ""}`}
                        onClick={() => setSelectedId(id)}
                      >
                        <span className="canvas-node__signal" aria-hidden="true" />
                        <span className="canvas-node__body">
                          <strong>{task.goal || id}</strong>
                          <small>{statusLabel(status)}</small>
                        </span>
                        <span className="canvas-node__priority">P{task.priority ?? 0}</span>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
            {columns.length > 1 ? <div className="canvas-board__flow" aria-hidden="true" /> : null}
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
                <div><dt>优先级</dt><dd>P{selectedTask.priority ?? 0}</dd></div>
                <div><dt>延迟预算</dt><dd>{selectedTask.latency_budget ?? 10}s</dd></div>
                <div><dt>依赖</dt><dd>{selectedTask.dependency?.length ? selectedTask.dependency.join(", ") : "无"}</dd></div>
              </dl>
            </aside>
          ) : null}
        </div>
      )}
    </section>
  );
}
