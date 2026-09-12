// date: 2026-08-17
// dev: 陈子毅
// changelog: AP4.6 新增人机协同回传服务——将 ChatView 中人类点选的选项尽力回传后端

import { apiClient } from "@/lib/api-client";

export interface HumanAnswerRequest {
  task_id: string;
  agent: string;
  answer: string;
}

export const humanApi = {
  // 集成点：后端需提供人类回答通道（REST POST /human/answer 或 WS）。
  // 当前 backend 的 HITL 由 AutoAskHandler 即时降级，人类回传为前向兼容钩子;
  // 该端点尚未在 backend 实现时调用会失败，调用方应吞掉错误、仅依赖乐观 UI。
  submitAnswer: (body: HumanAnswerRequest): Promise<void> =>
    apiClient.post<void>("/human/answer", body),
};
