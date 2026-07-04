// date: 2026-07-05
// dev: Claude Code (glm-5.2)
// changelog: 前端命名对齐后端——从 mappers/apimappers/ 迁移至 lib/api-client/，barrel 导出 apiClient + ApiClientError

export { apiClient, ApiClientError } from "./client";
export type { ApiClient } from "./client";
