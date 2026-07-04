// @aegis-gen
// date: 2026-07-04
// dev: Claude Code (glm-5.2)
// change: 接入统一配置——baseURL/webServer URL 改从环境变量读取
// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 playwright.config.ts，E2E 测试配置

import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = process.env.AEGIS_FRONTEND_PORT ?? "5173";
const FRONTEND_HOST = process.env.AEGIS_FRONTEND_HOST ?? "localhost";
const BASE_URL = `http://${FRONTEND_HOST}:${FRONTEND_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
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
