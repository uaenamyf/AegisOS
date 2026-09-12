// date: 2026-09-12
// dev: OpenSquilla
// changelog: 新建 agentActivity 模块——从全局事件流派生 Agent 活跃状态，
// 修复 Monitor 永远 idle 的问题（后端注册表状态是静态的，活跃度只能从事件推断）

import { useAppStore } from "@/lib/store";
import type { AgentStatus } from "@/protocol/types";

/** 单个 agent 的活跃记录：最近事件 + 时间戳 + 关联演练 */
export interface AgentActivity {
  agent: string;
  label: string;
  stage: string; // red | blue | purple | ""
  status: AgentStatus;
  /** 最近一次活动的 epoch ms；空闲判定：超过 IDLE_MS 降回 idle */
  lastActive: number;
  drillId?: string;
}

const IDLE_MS = 12_000; // 12s 无活动即视为空闲（真实 LLM 单 agent 步骤可达数分钟，容忍期放宽）
const tracked = new Map<string, AgentActivity>();
const subscribers = new Set<() => void>();

/** 演练运行状态：drill_id -> running|done|error（drill.status 事件驱动） */
const drillStates = new Map<string, string>();

function notify(): void {
  subscribers.forEach((fn) => fn());
  useAppStore.setState({ agentActivityVersion: Date.now() });
}

/** 供事件控制器调用：处理 drill.agent / drill.status / drill.round 事件 */
export function handleAgentActivityEvent(eventType: string, payload: Record<string, any> | undefined): void {
  const now = Date.now();
  if (eventType === "drill.agent") {
    const agent = String(payload?.agent ?? "");
    if (!agent) return;
    tracked.set(agent, {
      agent,
      label: String(payload?.label ?? agent),
      stage: String(payload?.stage ?? ""),
      status: "running",
      lastActive: now,
      drillId: payload?.drill_id ? String(payload.drill_id) : undefined,
    });
    notify();
  } else if (eventType === "drill.status") {
    const drillId = String(payload?.drill_id ?? "");
    const status = String(payload?.status ?? "");
    if (drillId) drillStates.set(drillId, status);
    // 演练结束：该演练的全部 agent 归位 idle
    if (status !== "running") {
      for (const [agent, rec] of tracked) {
        if (!rec.drillId || rec.drillId === drillId) {
          tracked.set(agent, { ...rec, status: "idle" });
        }
      }
      notify();
    }
  } else if (eventType === "drill.round") {
    // 轮完成：该演练 agent 短暂归位后随下一阶段事件再次点亮；
    // 这里仅刷新时间戳保持“活跃”观感连续
    for (const [agent, rec] of tracked) {
      if (rec.status === "running") tracked.set(agent, { ...rec, lastActive: now });
    }
    notify();
  }
}

/** 定时衰减：超过 IDLE_MS 未活动的 running agent 降级 idle（由 Monitor 组件定时调用） */
export function decayAgentActivity(): void {
  const now = Date.now();
  let changed = false;
  for (const [agent, rec] of tracked) {
    if (rec.status === "running" && now - rec.lastActive > IDLE_MS) {
      tracked.set(agent, { ...rec, status: "idle" });
      changed = true;
    }
  }
  if (changed) notify();
}

/** 订阅变化（Monitor 组件挂载时） */
export function subscribeAgentActivity(fn: () => void): () => void {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

/** 读取全部活跃记录（快照） */
export function getAgentActivity(): AgentActivity[] {
  return [...tracked.values()].sort((a, b) => b.lastActive - a.lastActive);
}

/** 当前是否有演练在跑 */
export function isAnyDrillRunning(): boolean {
  for (const status of drillStates.values()) {
    if (status === "running") return true;
  }
  return [...tracked.values()].some((r) => r.status === "running");
}
