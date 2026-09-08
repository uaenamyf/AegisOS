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

  /**
   * 配置云侧 LLM API Key 并同步到后端（即时生效）。
   * 端/边暂不单独配置，统一走云 API。
   *
   * @param persist true=落盘 tooling/configs/.env（重启后端仍有效）；
   *                false=仅存当前后端进程内存（后端重启即失效，硬盘无副本）。
   */
  setApiKey: (apiKey: string, persist = true): Promise<SystemModeInfo> =>
    apiClient.post<SystemModeInfo>("/system/api-key", {
      api_key: apiKey,
      persist,
    }),

  /** 查询 Key 可用性与持久化方式（不回显 Key）。 */
  getApiKeyStatus: (): Promise<{ has_key: boolean; persisted: boolean }> =>
    apiClient.get<{ has_key: boolean; persisted: boolean }>("/system/api-key/status"),

  /** 清除本机 Key：删除 .env 落盘副本并清空进程环境变量。 */
  deleteApiKey: (): Promise<SystemModeInfo> =>
    apiClient.del<SystemModeInfo>("/system/api-key"),
};
