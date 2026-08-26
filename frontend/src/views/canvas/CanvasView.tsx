// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/canvas/CanvasView.tsx，任务画布占位（DAG 编辑器占位）

import { useAppStore } from "@/lib/store";

export function CanvasView() {
  const tasks = useAppStore((s) => s.tasks);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">Task Canvas</h2>
        <p className="view__desc">
          DAG editor for task orchestration. Define goals, dependencies, and
          execution plans.
        </p>
      </header>

      <div className="view__body view__empty">
        {tasks.length === 0 ? (
          <p className="view__empty-text">
            No tasks yet. Create a task to begin building the execution DAG.
          </p>
        ) : (
          <ul className="view__list">
            {tasks.map((t) => (
              <li key={t.task_id} className="view__list-item">
                <span className="view__list-label">{t.goal || t.task_id}</span>
                <span className={`badge badge--${t.status ?? "pending"}`}>
                  {t.status ?? "pending"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
