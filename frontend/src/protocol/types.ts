// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 自动生成的 TypeScript 类型定义（由 tooling/scripts/gen_ts_types.py 生成，请勿手动编辑）

/* eslint-disable */
// @ts-nocheck
// This file is auto-generated from protocol/*.py — DO NOT EDIT MANUALLY.
// Run `python3 tooling/scripts/gen_ts_types.py` or `npm run gen:types` to regenerate.

// === Enums / Union types ===

export type AgentStatus = "idle" | "running" | "waiting" | "failed" | "offline";

export type EventType = "agent.start" | "agent.finish" | "tool.call" | "tool.finish" | "task.retry" | "task.rollback" | "memory.update" | "graph.update";

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
  plan?: Record<string, any>;
  status?: any;
  retry?: any;
  rollback?: any;
  dependency?: any[];
  priority?: number;
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

// === Frontend-specific types (not from protocol/) ===

export type ViewName = 'chat' | 'canvas' | 'graph' | 'monitor' | 'replay';

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

export interface ApiError {
  code: string;
  message: string;
  trace_id: string;
}

export interface Session {
  id: string;
  user_id: string;
  status: 'active' | 'closed';
  context: Record<string, any>;
  created_at?: string;
}

export interface CreateSessionRequest {
  user_id: string;
}

export interface CreateTaskRequest {
  goal: string;
  session_id: string;
}

export interface InvokeAgentRequest {
  goal: string;
  session_id: string;
}

export interface InvokeToolRequest {
  name: string;
  args: Record<string, any>;
}

export interface WriteMemoryRequest {
  working?: Record<string, any>;
  semantic?: Record<string, any>;
  episodic?: Record<string, any>;
  archive?: Record<string, any>;
  summary?: string;
}

export interface Metrics {
  uptime_seconds: number;
  agents_registered: number;
  events_buffered: number;
  db_engine: string;
  status: string;
}

export interface ReplayResponse {
  session_id: string;
  timeline: any[];
  event_count: number;
}
