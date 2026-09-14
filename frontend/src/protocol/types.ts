// date: 2026-06-27
// dev: myf
// changelog: 自动生成的 TypeScript 类型定义（由 tooling/scripts/gen_ts_types.py 生成，请勿手动编辑）

/* eslint-disable */
// @ts-nocheck
// This file is auto-generated from protocol/*.py — DO NOT EDIT MANUALLY.
// Run `python3 tooling/scripts/gen_ts_types.py` or `npm run gen:types` to regenerate.

// === Enums / Union types ===

export type AgentStatus = "idle" | "running" | "waiting" | "failed" | "offline";

// date: 2026-08-17
// dev: 陈子毅
// changelog: AP4.5/AP4.6 新增人机协同事件类型 human.input.required / human.response（对应 protocol/event.py EventType）
export type EventType = "agent.start" | "agent.finish" | "tool.call" | "tool.finish" | "task.retry" | "task.rollback" | "memory.update" | "graph.update" | "human.input.required" | "human.response";

export type NodeKind = "agent" | "task" | "memory" | "tool";

export type SyncStatus = "pending" | "in_flight" | "applied" | "conflict" | "failed";

export type TaskStatus = "pending" | "running" | "succeeded" | "failed" | "rolled_back" | "cancelled";

// === Interfaces ===

export interface Agent {
  agent_id: string;
  name: string;
  role: string;
  ref?: any;
  capabilities?: any[];
  status?: any;
  trust_score?: number;
  success_rate?: number;
}

export interface Alert {
  alert_id: string;
  severity?: string;
  src?: string;
  dst?: string;
  technique?: string;
  raw?: Record<string, any>;
}

export interface Asset {
  asset_id: string;
  host?: string;
  services?: any[];
  os?: string;
  exposure?: string;
}

export interface AttackChain {
  chain_id: string;
  target?: string;
  steps?: any[];
  status?: string;
}

export interface AttackStep {
  step_id: string;
  technique?: string;
  from_asset?: string;
  to_asset?: string;
  success?: boolean;
}

export interface DefenseAction {
  action_id: string;
  kind?: string;
  target?: string;
  rationale?: string;
}

export interface Event {
  event_id?: string;
  event_type?: any;
  task_id?: string;
  source?: any;
  payload?: Record<string, any>;
  timestamp?: number;
}

export interface Graph {
  nodes?: Record<string, any>;
  edges?: any[];
}

export interface GraphDiff {
  added_nodes?: any[];
  removed_nodes?: any[];
  added_edges?: any[];
  removed_edges?: any[];
  updated_edges?: any[];
}

export interface GraphEdge {
  src: string;
  dst: string;
  weight?: number;
  entropy?: number;
  latency?: number;
  trust_score?: number;
  success_rate?: number;
}

export interface GraphNode {
  node_id: string;
  kind: any;
  name?: string;
  capabilities?: any[];
  trust_score?: number;
  success_rate?: number;
  latency?: number;
  status?: string;
}

export interface Header {
  version?: string;
  trace_id?: string;
  session_id?: string;
  compress?: string;
}

export interface Heartbeat {
  node?: any;
  cpu?: number;
  gpu?: number;
  latency?: number;
  memory?: number;
  token?: number;
  status?: string;
  timestamp?: number;
}

export interface MemoryPacket {
  working?: Record<string, any>;
  semantic?: Record<string, any>;
  episodic?: Record<string, any>;
  archive?: Record<string, any>;
  embedding?: any[];
  summary?: string;
  compression?: Record<string, any>;
  session_id?: string;
  task_id?: string;
  kind?: string;
  recent?: boolean;
}

export interface Message {
  message_id?: string;
  parent_id?: string;
  task_id?: string;
  workflow_id?: string;
  sender?: any;
  receiver?: any;
  priority?: number;
  ttl?: number;
  compression?: string;
  timestamp?: number;
  payload?: any;
  header?: any;
}

export interface NodeRef {
  node_id: string;
  node_type: string;
  name?: string;
}

export interface Plan {
  plan_id?: string;
  goal?: string;
  dag?: Record<string, any>;
  tasks?: any[];
}

export interface ResponsePlan {
  plan_id: string;
  actions?: any[];
  confidence?: number;
  rollback?: Record<string, any>;
}

export interface RetryPolicy {
  max_attempts?: number;
  backoff?: number;
}

export interface RollbackPlan {
  enabled?: boolean;
  steps?: any[];
}

export interface Route {
  task_id: string;
  path?: any[];
  cost?: number;
  entropy?: number;
}

export interface Schedule {
  schedule_id?: string;
  task_id?: string;
  assigned_to?: string;
  queued_at?: number;
  priority?: number;
}

export interface SyncPacket {
  sync_id?: string;
  source?: string;
  target?: string;
  payload?: Record<string, any>;
  status?: any;
  vector_clock?: Record<string, any>;
  timestamp?: number;
}

export interface Task {
  task_id?: string;
  goal?: string;
  payload?: Record<string, any>;
  plan?: Record<string, any>;
  result?: Record<string, any>;
  status?: any;
  retry?: any;
  rollback?: any;
  dependency?: any[];
  priority?: number;
  privacy?: string;
  latency_budget?: number;
}

// date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 补充 ThreatIntel ATT&CK 映射字段 + 攻防响应类型
export interface ThreatIntel {
  technique?: string;
  tactic?: string;
  refs?: any[];
  technique_id?: string;
  sub_technique?: string;
  detection?: string;
  mitigation?: string;
  risk_level?: string;
  asset_ids?: any[];
}

// --- 攻防场景响应类型（对应后端 backend/schemas/__init__.py）---

export interface RangeResponse {
  range_id: string;
  target_range: string;
  label: string;
  status: string;
  topology: TopologyResponse;
}

export interface TopologyResponse {
  target_range: string;
  nodes: Record<string, any>[];
  edges: Record<string, any>[];
}

// ---- R15 可观测性：逐 agent 输入输出追踪 ----
export interface AgentTraceEntry {
  agent: string;
  input: string;
  output: Record<string, any> | string;
}

export interface RedAttackResponse {
  assets: Asset[];
  findings: VulnFinding[];
  chain: Record<string, any>;
  agent_trace?: AgentTraceEntry[];
}

// ---- 红队攻击流式（SSE 渐进展示）----
// date: 2026-09-05
// changelog: 新增——与 backend/routers/attack.py 的 /attack/stream 契约对齐
// （事件名锚点：stage_start / stage_done / done / attack_error）
export type RedAttackStreamEventName =
  | "stage_start"
  | "stage_done"
  | "done"
  | "attack_error";

export interface RedAttackStreamEvent {
  name: RedAttackStreamEventName;
  data: Record<string, any>;
}

export interface BlueDefenseResponse {
  alerts: Alert[];
  triaged: Alert[];
  hypotheses: Record<string, any>[];
  plan: Record<string, any>;
  agent_trace?: AgentTraceEntry[];
}

// ---- T1 蓝队流式（SSE 渐进展示）----
// date: 2026-09-06
// changelog: 新增——与 backend/routers/defense.py 的 /defense/stream 契约对齐
// （事件名锚点：stage_start / stage_done / done / defense_error）
export type BlueDefenseStreamEventName =
  | "stage_start"
  | "stage_done"
  | "done"
  | "defense_error";

export interface BlueDefenseStreamEvent {
  name: BlueDefenseStreamEventName;
  data: Record<string, any>;
}

export interface PurpleReviewResponse {
  critique: Record<string, any>;
  review: Record<string, any>;
  agent_trace?: AgentTraceEntry[];
}

// ---- CyberDrill（多轮攻防演练）----
// date: 2026-09-04 dev: AegisOS Dev
// changelog: R4 新增 drill 类型——与 backend/routers/drill.py 契约严格对齐（事件名锚点）

// ---- 运行时模式（R7：mock / 真实 LLM 切换）----
// date: 2026-09-04 dev: AegisOS Dev
// changelog: R7 新增——与 backend/routers/system.py 契约对齐

export type RuntimeMode = "mock" | "real";

export interface SystemModeInfo {
  mode: RuntimeMode;
  model: string;
  provider: string;
  has_key: boolean;
  available: RuntimeMode[];
  /** Key 是否已落盘 .env（false = 仅后端进程内存，重启失效）。 */
  persisted?: boolean;
}
export interface StartDrillRequest {
  target_range?: string;
  max_rounds?: number;
}

export interface StartDrillResponse {
  drill_id: string;
  status: DrillStatus;
  max_rounds: number;
}

export interface DrillRoundRed {
  ok: boolean;
  assets: string[];
  finding_count: number;
  steps: Record<string, any>[];
  new_steps: Record<string, any>[];
  agent_trace?: AgentTraceEntry[];
}

export interface DrillRoundBlue {
  ok: boolean;
  alerts: Record<string, any>[];
  triaged_count: number;
  plan: Record<string, any>;
  agent_trace?: AgentTraceEntry[];
}

export interface DrillRoundPurple {
  ok: boolean;
  critique: Record<string, any>;
  review: Record<string, any>;
  converged: boolean;
  valid: boolean;
  new_issue_count: number;
  agent_trace?: AgentTraceEntry[];
}

/** R10: 演练阶段执行位置标注（端-边-云自适应调度）。 */
export interface DrillPhasePlacement {
  tier: "device" | "edge" | "cloud";
  model_id: string;
  reason: string;
}

export interface DrillRoundPhases {
  red: DrillPhasePlacement;
  blue: DrillPhasePlacement;
  purple: DrillPhasePlacement;
}

export interface DrillRound {
  round: number;
  red: DrillRoundRed;
  blue: DrillRoundBlue;
  purple: DrillRoundPurple;
  /** R10: 三阶段执行位置标注。 */
  phase?: DrillRoundPhases;
  /** R8: 跨轮记忆——本轮紫队携带的前序轮次决策摘要（首轮为 null）。 */
  prior_rounds_summary?: string | null;
  event_stream: Record<string, any>[];
  convergence_code: string;
}

export interface DrillMemoryTraceEntry {
  round: number;
  stored_task_id: string;
  packet_summary: string;
  compressed_count: number;
  next_round_summary: string | null;
}

export interface DrillSummaryResponse {
  conclusion: string;
  convergence_code: string;
  rounds_executed: number;
  /** R8: 跨轮记忆轨迹——每轮写入的记忆包 + 为下一轮生成的摘要。 */
  memory_trace?: DrillMemoryTraceEntry[];
}

export interface DrillRecord {
  drill_id: string;
  target_range: string;
  max_rounds: number;
  rounds_executed: number;
  convergence_code: string;
  rounds: DrillRound[];
  summary: DrillSummaryResponse;
  created_at?: string;
  /** 运行中轮询用：running | done | aborted（后端 DrillRuntime.state） */
  status?: string;
  error?: string | null;
  /** 切页返回恢复用：当前阶段 / 当前轮 / 已进时间（秒）/ CoT agent 轨迹 */
  current_stage?: string | null;
  current_round?: number;
  elapsed?: number;
  agent_trace?: DrillAgentTraceEntry[];
}

/** CoT 推理时间线条目（后端 drill_agent 事件载荷）。 */
export interface DrillAgentTraceEntry {
  drill_id?: string;
  stage: string;
  agent: string;
  label: string;
  round?: number;
  ts: number;
  /** R20 端边云路由：该 agent 真实执行的层级/节点/耗时（下一次调用前为上一跳结果） */
  tier?: string | null;
  node_id?: string | null;
  latency_ms?: number | null;
  reason?: string | null;
}

// T7: 历史演练元信息（GET /drill/list）
export interface DrillMeta {
  drill_id: string;
  target_range: string;
  rounds_executed: number;
  convergence_code: string;
  created_at?: string;
}

/** SSE 事件名（锚点：backend/routers/drill.py 的 emit 调用）。 */
export type DrillEventName =
  | "drill_start"
  | "drill_round"
  | "drill_stage"
  | "drill_agent"
  | "drill_summary"
  | "drill_done"
  | "drill_error";

export interface DrillEvent {
  name: DrillEventName;
  data: Record<string, any>;
}

export interface ToolCall {
  call_id?: string;
  name?: string;
  args?: Record<string, any>;
  timeout?: number;
  permission?: string;
}

export interface ToolResult {
  call_id?: string;
  ok?: boolean;
  output?: any;
  error?: string;
  meta?: Record<string, any>;
}

export interface ToolSpec {
  name: string;
  description?: string;
  args_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  permission?: string;
  resource_limit?: Record<string, any>;
}

export interface VulnFinding {
  finding_id: string;
  cve_id?: string;
  asset_id?: string;
  cvss?: number;
  attack_surface?: string;
}
