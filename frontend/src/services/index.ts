// date: 2026-07-05
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/index.ts，barrel 导出全部前端服务（对应后端 routers/__init__.py 聚合模式）

// REST API 服务（对应后端 routers/）
export { sessionApi } from "./api/sessions";
export type { CreateSessionRequest } from "./api/sessions";
export { taskApi } from "./api/tasks";
export type { CreateTaskRequest, ListTasksResponse } from "./api/tasks";
export { agentApi } from "./api/agents";
export type { InvokeAgentRequest, InvokeAgentResponse, InvokeToolRequest, ListAgentsResponse } from "./api/agents";
export { memoryApi } from "./api/memory";
export { graphApi } from "./api/graph";

// date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 新增攻防 API 服务导出
export { cyberApi } from "./api/cyber";
export type {
  StartRangeRequest,
  RedAttackRequest,
  BlueDefenseRequest,
  PurpleReviewRequest,
} from "./api/cyber";

// 实时通信服务（对应后端 sse.py + ws.py）
export { SseManager, sseManager } from "./realtime/sse";
export type { SseHandler } from "./realtime/sse";
export { WsManager, wsManager } from "./realtime/ws";
export type { WsHandler } from "./realtime/ws";

// 状态编排服务（对应后端 services/ 业务逻辑）
export { sessionService } from "./session";
export { graphService } from "./graph";
