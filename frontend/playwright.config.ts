// date: 2026-07-04
// dev: Claude Code (glm-5.2)
// changelog: 接入统一配置——baseURL/webServer URL 改从环境变量读取

import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = process.env.AEGIS_FRONTEND_PORT ?? "5173";
const FRONTEND_HOST = process.env.AEGIS_FRONTEND_HOST ?? "localhost";
const BASE_URL = `http://${FRONTEND_HOST}:${FRONTEND_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  // 串行执行：本项目的 e2e 共用同一个后端进程，且 settings 用例会 POST
  // /infra/configure 重建全进程共享的节点注册表——并发跑会互相把对方的在线节点换掉。
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
