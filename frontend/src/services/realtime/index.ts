// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/realtime/index.ts，barrel 导出 SSE/WS 管理器

export { SseManager, sseManager } from "./sse";
export type { SseHandler } from "./sse";
export { WsManager, wsManager } from "./ws";
export type { WsHandler } from "./ws";
