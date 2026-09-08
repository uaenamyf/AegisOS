// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R7 新建 services/api/system.ts——运行时模式查询/切换（对应 backend/routers/system.py）

import { apiClient } from "@/lib/api-client";
import type { RuntimeMode, SystemModeInfo } from "@/protocol/types";

export const systemApi = {
  /** 查询当前运行时模式（mock / 真实 LLM + 模型/提供商信息）。 */
  getMode: (): Promise<SystemModeInfo> => apiClient.get<SystemModeInfo>("/system/mode"),

  /** 切换运行时模式（mock=预置响应 / real=真实 LLM）。 */
  setMode: (mode: RuntimeMode): Promise<SystemModeInfo> =>
    apiClient.post<SystemModeInfo>("/system/mode", { mode }),
};
