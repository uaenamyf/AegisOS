// date: 2026-09-12
// dev: OpenSquilla
// changelog: 新建 agentActivity 模块——从全局事件流派生 Agent 活跃状态，
// 修复 Monitor 永远 idle 的问题（后端注册表状态是静态的，活跃度只能从事件推断）
// changelog: 2026-09-12 晚 移除 12s 定时休眠——真实 LLM 单步 30-90s，定时器会把
// 正在工作的 agent 误判为空闲。改为纯事件驱动状态机：agent 只有在「下一个
// agent 启动（把前一个顶掉）」或「演练结束」时才改变状态，无任何超时定时器。

import { useAppStore } from "@/lib/store";
import type { AgentStatus } from "@/protocol/types";

/** 单个 agent 的活跃记录：最近事件 + 时间戳 + 关联演练 */
export interface AgentActivity {
  agent: string;
  label: string;
  stage: string; // red | blue | purple | ""
  status: AgentStatus;
  /** 最近一次活动的 epoch ms（仅用于展示"多久之前"，不参与状态判定） */
  lastActive: number;
  drillId?: string;
}

const tracked = new Map<string, AgentActivity>();
const subscribers = new Set<() => void>();

/** 演练运行状态：drill_id -> running|done|error（drill.status 事件驱动） */
const drillStates = new Map<string, string>();

/** 当前每场演练正在执行的 agent：drill_id -> agent id（用于演练结束时只归位参与者） */
const activeAgentByDrill = new Map<string, string>();

function notify(): void {
  subscribers.forEach((fn) => fn());
  useAppStore.setState({ agentActivityVersion: Date.now() });
}

/** 供事件控制器调用：处理 drill.agent / drill.status / drill.round 事件 */
export function handleAgentActivityEvent(
  eventType: string,
  payload: Record<string, any> | undefined,
): void {
  const now = Date.now();
  if (eventType === "drill.agent") {
    const drillId = payload?.drill_id ? String(payload.drill_id) : "";
    const agent = String(payload?.agent ?? "");
    if (!agent) return;
    // 同一场演练内同时只有一个 agent 在执行：新 agent 启动时把上一个顶掉
    // （顺序流水线：红3 → 蓝4 → 紫2），其余演练的 agent 不受影响
    const prev = drillId ? activeAgentByDrill.get(drillId) : undefined;
    if (prev && prev !== agent) {
      const prevRec = tracked.get(prev);
      if (prevRec && (!drillId || prevRec.drillId === drillId)) {
        tracked.set(prev, { ...prevRec, status: "idle" });
      }
    }
    if (drillId) activeAgentByDrill.set(drillId, agent);
    tracked.set(agent, {
      agent,
      label: String(payload?.label ?? agent),
      stage: String(payload?.stage ?? ""),
      status: "running",
      lastActive: now,
      drillId: drillId || undefined,
    });
    notify();
  } else if (eventType === "drill.status") {
    const drillId = String(payload?.drill_id ?? "");
    const status = String(payload?.status ?? "");
    if (drillId) drillStates.set(drillId, status);
    // 演练结束：该演练的全部 agent 归位 idle（事件驱动，非定时）
    if (status !== "running") {
      for (const [agent, rec] of tracked) {
        if (!rec.drillId || rec.drillId === drillId) {
          tracked.set(agent, { ...rec, status: "idle" });
        }
      }
      activeAgentByDrill.delete(drillId);
      notify();
    }
  } else if (eventType === "drill.round") {
    // 轮完成：仅刷新时间戳（观感连续），状态本身不变——下一个阶段的
    // drill.agent 事件会按上面规则接管
    for (const [agent, rec] of tracked) {
      if (rec.status === "running") tracked.set(agent, { ...rec, lastActive: now });
    }
    notify();
  }
}

/** 兼容保留：无操作（历史版本有 12s 定时休眠，已按用户要求移除） */
export function decayAgentActivity(): void {
  /* 纯事件驱动：无定时衰减 */
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
