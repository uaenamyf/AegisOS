// date: 2026-08-27
// dev: ox-alpha
// R11: Monitor 视图增强 —— 端边云节点面板 + 调度沙盒
// 2026-09-12: Agent 活跃状态真实化——从事件流派生 running/idle，不再永远 idle

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { InfraNodePanel } from "@/components/InfraNodePanel";
import { DispatchSandbox } from "@/components/DispatchSandbox";
import {
  getAgentActivity,
  isAnyDrillRunning,
  subscribeAgentActivity,
  type AgentActivity,
} from "@/services/agentActivity";

const STAGE_LABEL: Record<string, string> = {
  red: "红队",
  blue: "蓝队",
  purple: "紫队",
};

function sinceText(ms: number): string {
  const s = Math.max(0, Math.floor((Date.now() - ms) / 1000));
  if (s < 60) return `${s}s 前`;
  return `${Math.floor(s / 60)}m${String(s % 60).padStart(2, "0")}s 前`;
}

export function MonitorView() {
  const agents = useAppStore((s) => s.agents);
  const version = useAppStore((s) => s.agentActivityVersion);
  const [, forceTick] = useState(0);
  const [activities, setActivities] = useState<AgentActivity[]>([]);

  // 订阅活跃状态变化（纯事件驱动，无定时休眠）+ 相对时间跳动
  useEffect(() => {
    const unsub = subscribeAgentActivity(() => setActivities(getAgentActivity()));
    const tickTimer = window.setInterval(() => {
      setActivities(getAgentActivity());
      forceTick((t) => t + 1);
    }, 5000);
    setActivities(getAgentActivity());
    return () => {
      unsub();
      window.clearInterval(tickTimer);
    };
  }, []);

  const activityByAgent = new Map(activities.map((a) => [a.agent, a]));
  const drillRunning = isAnyDrillRunning();
  void version; // 活跃模块通过 store 版本号触发重渲染

  return (
    <section className="view">
      <header className="view__header">
        <h2 className="view__title">运行监控</h2>
        <p className="view__desc">
          端边云资源状态 · Agent 实时监控 · 调度沙盒
        </p>
      </header>

      {/* 演练运行状态条：任何演练 running 时置顶可见 */}
      <div className={`monitor-drill-status${drillRunning ? " monitor-drill-status--running" : ""}`}>
        <span className={`monitor-drill-status__dot${drillRunning ? " monitor-drill-status__dot--live" : ""}`} />
        {drillRunning ? "演练执行中 —— 活跃 Agent 见下方实时状态" : "当前无演练运行（在 Cyber Defense 发起后这里会实时亮起）"}
      </div>

      <div className="view__body monitor-view__body">
        {/* R11: 端边云节点面板 */}
        <InfraNodePanel />

        {/* R11: 调度沙盒 */}
        <DispatchSandbox />

        {/* 实时活跃 Agent（事件驱动，非静态注册表） */}
        <div>
          <h3 className="view__section-title">Agent 实时活动</h3>
          {activities.length === 0 ? (
            <p className="view__empty-text">
              暂无实时活动。发起攻防演练后，红/蓝/紫各 Agent 的执行会实时显示在这里。
            </p>
          ) : (
            <ul className="view__list">
              {activities.map((a) => (
                <li key={a.agent} className="view__list-item">
                  <span className="view__list-label">
                    {a.label}{" "}
                    <span className="view__list-sub">
                      ({a.agent} · {STAGE_LABEL[a.stage] ?? (a.stage || "-")} · {sinceText(a.lastActive)})
                    </span>
                  </span>
                  <span className={`badge badge--${a.status}`}>
                    {a.status === "running" ? "执行中" : "空闲"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 注册 Agent 列表（静态注册表 + 事件派生状态叠加） */}
        <div>
          <h3 className="view__section-title">注册 Agent</h3>
          {agents.length === 0 ? (
            <p className="view__empty-text">
              暂无已注册 Agent。Agent 加入协作网络后会显示在这里。
            </p>
          ) : (
            <ul className="view__list">
              {agents.map((a) => {
                const live = activityByAgent.get(String(a.agent_id ?? a.name));
                const status = live?.status === "running" ? "running" : (a.status ?? "idle");
                return (
                  <li key={a.agent_id} className="view__list-item">
                    <span className="view__list-label">
                      {a.name}{" "}
                      <span className="view__list-sub">({a.role})</span>
                    </span>
                    <span className={`badge badge--${status}`}>
                      {status === "running" ? "执行中" : status}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
