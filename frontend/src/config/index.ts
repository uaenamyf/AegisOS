// @aegis-gen
// date: 2026-07-04
// dev: Claude Code (glm-5.2)
// change: 新建前端统一配置入口——所有 API 地址/端口/密钥/WS 地址统一从 config/index.ts 导出
/**
 * AegisOS 前端统一配置。
 *
 * 优先级（高 → 低）:
 *   1. import.meta.env.VITE_*（由 frontend/.env 注入）
 *   2. 代码默认值（与 tooling/configs/defaults.yaml 保持同步）
 *
 * 用法:
 *   import { config } from "@/config";
 *   config.apiBaseUrl   // "http://localhost:8000/api/v1"
 *   config.wsUrl        // "ws://localhost:8000/ws/v1/stream"
 *   config.apiKey       // "aegis-dev-key"
 */

// --- 类型 -------------------------------------------------------------------

export interface AppConfig {
  /** REST API 基址，如 http://localhost:8000/api/v1 */
  apiBaseUrl: string;
  /** WebSocket 地址，如 ws://localhost:8000/ws/v1/stream */
  wsUrl: string;
  /** SSE 事件流地址，如 http://localhost:8000/api/v1/events */
  sseUrl: string;
  /** API 鉴权 Key（X-API-Key header） */
  apiKey: string;
  /** API Key header 名称 */
  apiKeyHeader: string;
  /** Trace ID header 名称 */
  traceHeader: string;
  /** Session ID header 名称 */
  sessionHeader: string;
}

// --- 实现 -------------------------------------------------------------------

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_WS_URL = "ws://localhost:8000/ws/v1/stream";

function env(key: string): string | undefined {
  const val = import.meta.env[key] as string | undefined;
  return val && val.length > 0 ? val : undefined;
}

export const config: AppConfig = {
  apiBaseUrl: env("VITE_API_BASE_URL") ?? DEFAULT_API_BASE_URL,
  wsUrl: env("VITE_WS_URL") ?? DEFAULT_WS_URL,

  get sseUrl(): string {
    // SSE 端点 = apiBaseUrl 去掉 /api/v1 后缀 + /api/v1/events
    return this.apiBaseUrl.replace(/\/api\/v1\/?$/, "/api/v1/events");
  },

  apiKey: env("VITE_API_KEY") ?? "aegis-dev-key",
  apiKeyHeader: "X-API-Key",
  traceHeader: "X-Trace-Id",
  sessionHeader: "X-Session-Id",
};
