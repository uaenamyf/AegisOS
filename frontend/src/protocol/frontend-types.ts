// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建前端专用类型定义（非 protocol 契约类型，由前端自行维护）

// === Frontend-specific types (not auto-generated) ===

export type ViewName = 'canvas' | 'graph' | 'monitor' | 'replay';

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
  context: Record<string, unknown>;
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
  args: Record<string, unknown>;
}

export interface WriteMemoryRequest {
  working?: Record<string, unknown>;
  semantic?: Record<string, unknown>;
  episodic?: Record<string, unknown>;
  archive?: Record<string, unknown>;
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
  timeline: unknown[];
  event_count: number;
}
