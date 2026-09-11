// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 views/replay/ReplayView.tsx，回放时间线占位

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";
import type { Event } from "@/protocol/types";

const EVENT_META: Record<string, { label: string; phase: string; tone: string }> = {
  "agent.start": { label: "智能体开始执行", phase: "执行开始", tone: "running" },
  "agent.finish": { label: "智能体完成任务", phase: "执行完成", tone: "success" },
  "tool.call": { label: "调用工具", phase: "工具调用", tone: "accent" },
  "tool.finish": { label: "工具返回结果", phase: "工具调用", tone: "success" },
  "graph.update": { label: "协作拓扑更新", phase: "状态同步", tone: "accent" },
  "memory.update": { label: "记忆状态更新", phase: "状态同步", tone: "accent" },
  "task.retry": { label: "任务重试", phase: "异常处理", tone: "warning" },
  "task.rollback": { label: "任务回滚", phase: "异常处理", tone: "danger" },
  "drill.round": { label: "攻防轮次完成", phase: "红蓝紫协同", tone: "accent" },
  "drill.summary": { label: "演练完成并收敛", phase: "演练总结", tone: "success" },
};

function eventMeta(type: string) {
  return EVENT_META[type] ?? { label: type || "未知事件", phase: "系统事件", tone: "accent" };
}

function eventAgent(event: Event): string {
  return String(event.source?.node_id ?? event.payload?.agent_id ?? "系统");
}

function eventSummary(event: Event): string {
  const payload = event.payload ?? {};
  if (event.event_type === "drill.round") {
    const red = payload.red ?? {};
    const blue = payload.blue ?? {};
    const purple = payload.purple ?? {};
    return `第 ${payload.round ?? "—"} 轮：红队新增 ${red.new_steps?.length ?? 0} 步，蓝队处置 ${blue.plan?.actions?.length ?? 0} 项，紫队${purple.valid ? "通过校验" : `发现 ${purple.new_issue_count ?? 0} 个缺口`}`;
  }
  if (event.event_type === "drill.summary") {
    return payload.summary?.conclusion ?? `共完成 ${payload.rounds ?? 0} 轮，最终状态为 ${payload.convergence_code ?? "未知"}`;
  }
  if (typeof payload.output === "string") return payload.output;
  if (payload.output && typeof payload.output === "object") return JSON.stringify(payload.output);
  if (payload.goal) return String(payload.goal);
  if (payload.error) return `执行失败：${payload.error}`;
  if (event.event_type === "graph.update") return "协作拓扑已同步";
  return "已记录执行状态变化";
}

export function ReplayView() {
  const events = useAppStore((s) => s.events);
  const currentSession = useAppStore((s) => s.currentSession);
  const tasks = useAppStore((s) => s.tasks);
  const setEvents = useAppStore((s) => s.setEvents);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const currentEvent = events[cursor];

  const mergeEvents = (incoming: Event[]): Event[] => {
    const unique = new Map<string, Event>();
    for (const event of incoming) {
      const key = event.event_id ?? `${event.event_type}:${event.task_id ?? ""}:${event.timestamp ?? 0}`;
      unique.set(key, event);
    }
    return [...unique.values()].sort((left, right) => (left.timestamp ?? 0) - (right.timestamp ?? 0));
  };

  useEffect(() => {
    const sessionId = currentSession?.id;
    if (!sessionId) return;
    void apiClient
      .get<{ timeline: Event[] }>(`/replay/${encodeURIComponent(sessionId)}`)
      .then((response) => {
        const snapshotEvents: Event[] = [];
        try {
          const raw = sessionStorage.getItem("aegis.cyber-drill.snapshot");
          const snapshot = raw ? JSON.parse(raw) as { drillId?: string; rounds?: any[]; summary?: any } : null;
          if (snapshot?.drillId && snapshot.rounds?.length) {
            snapshot.rounds.forEach((round) => snapshotEvents.push({
              event_id: `${snapshot.drillId}:round:${round.round}`,
              event_type: "drill.round",
              task_id: snapshot.drillId,
              source: { node_id: "orchestrator" },
              payload: { drill_id: snapshot.drillId, round: round.round, red: round.red, blue: round.blue, purple: round.purple, convergence_code: round.convergence_code },
              timestamp: Date.now(),
            }));
            if (snapshot.summary) snapshotEvents.push({ event_id: `${snapshot.drillId}:summary`, event_type: "drill.summary", task_id: snapshot.drillId, source: { node_id: "orchestrator" }, payload: { summary: snapshot.summary, rounds: snapshot.rounds.length, convergence_code: snapshot.summary.convergence_code }, timestamp: Date.now() });
          }
        } catch { /* 快照损坏时忽略 */ }

        const currentEvents = useAppStore.getState().events;
        if (response.timeline?.length || currentEvents.length || snapshotEvents.length) {
          setEvents(mergeEvents([...response.timeline, ...currentEvents, ...snapshotEvents]));
        } else if (tasks.length) {
          setEvents(tasks.flatMap((task) => task.task_id ? [
            { event_id: `${task.task_id}-start`, event_type: "agent.start", task_id: task.task_id, payload: { goal: task.goal, session_id: sessionId }, timestamp: Date.now() },
            ...(task.status === "succeeded" || task.status === "failed" ? [{ event_id: `${task.task_id}-finish`, event_type: "agent.finish", task_id: task.task_id, payload: { output: task.result, session_id: sessionId }, timestamp: Date.now() }] : []),
          ] : []));
        }
      })
      .catch(() => { /* SSE 前端事件仍可用于即时回放 */ });
  }, [currentSession?.id, setEvents, tasks]);

  const loadDemoEvents = () => {
    const now = Date.now();
    setEvents([
      { event_id: "demo-1", event_type: "agent.start", task_id: "recon", timestamp: now - 3000 },
      { event_id: "demo-2", event_type: "tool.call", task_id: "recon", timestamp: now - 2000 },
      { event_id: "demo-3", event_type: "agent.finish", task_id: "recon", timestamp: now - 1000 },
      { event_id: "demo-4", event_type: "graph.update", task_id: "vuln", timestamp: now },
    ]);
    setCursor(0);
  };

  useEffect(() => {
    if (!playing || !events.length) return;
    const timer = window.setInterval(() => setCursor((current) => current >= events.length - 1 ? 0 : current + 1), 1200);
    return () => window.clearInterval(timer);
  }, [events.length, playing]);

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">事件回放</h2>
        <p className="view__desc">
          按时间回看当前会话的 Agent 执行事件与状态变化。
        </p>
      </header>

      <div className="view__body view__empty replay-shell">
        {events.length === 0 ? (
          <div className="replay-empty-state">
          <p className="view__empty-text">
            当前会话还没有可回放事件。开始一次 Chat 任务后，这里会自动记录执行轨迹。
          </p>
          <button type="button" className="canvas-demo-cta" onClick={loadDemoEvents}>加载演示回放</button>
          </div>
        ) : (
          <>
          <div className="view__metrics">
            <div className="metric"><span className="metric__value">{events.length}</span><span className="metric__label">实时事件</span></div>
            <div className="metric"><span className="metric__value">{new Set(events.map((event) => event.task_id).filter(Boolean)).size}</span><span className="metric__label">关联任务</span></div>
          </div>
          <div className="replay-controls">
            <button type="button" onClick={() => setPlaying((value) => !value)}>{playing ? "暂停" : "播放"}</button>
            <button type="button" onClick={() => setCursor((value) => Math.max(0, value - 1))}>上一步</button>
            <button type="button" onClick={() => setCursor((value) => Math.min(events.length - 1, value + 1))}>下一步</button>
            <input aria-label="回放进度" type="range" min="0" max={Math.max(0, events.length - 1)} value={cursor} onChange={(event) => setCursor(Number(event.target.value))} />
            <span>{cursor + 1} / {events.length}</span>
          </div>
          <ul className="view__timeline">
            {events.map((e, index) => (
              <li key={e.event_id ?? `${e.event_type}-${e.timestamp}`} className={`timeline__item timeline__item--${eventMeta(String(e.event_type)).tone}${index === cursor ? " timeline__item--active" : ""}`}>
                  <span className="timeline__type">{eventMeta(String(e.event_type)).label}</span>
                  <span className="timeline__phase">{eventMeta(String(e.event_type)).phase}</span>
                  <span className="timeline__task">{e.task_id ? `任务 ${e.task_id}` : "全局事件"}</span>
              </li>
            ))}
          </ul>
          {currentEvent ? <aside className="replay-detail" aria-label="当前事件详情">
            <span className="canvas-inspector__eyebrow">当前事件</span>
            <h3>{eventMeta(String(currentEvent.event_type)).label}</h3>
            <dl className="canvas-inspector__facts">
              <div><dt>任务</dt><dd>{currentEvent.task_id ?? "全局事件"}</dd></div>
              <div><dt>执行者</dt><dd>{eventAgent(currentEvent)}</dd></div>
              <div><dt>阶段</dt><dd>{eventMeta(String(currentEvent.event_type)).phase}</dd></div>
              <div><dt>时间</dt><dd>{currentEvent.timestamp ? new Date(currentEvent.timestamp).toLocaleTimeString() : "—"}</dd></div>
            </dl>
            <div className="replay-detail__summary"><span>事件说明</span><p>{eventSummary(currentEvent)}</p></div>
          </aside> : null}
          </>
        )}
      </div>
    </section>
  );
}
