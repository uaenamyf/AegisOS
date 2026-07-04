// @aegis-gen
// date: 2026-07-04
// dev: Claude Code (glm-5.2)
// change: 接入统一配置——proxy target 改从环境变量读取
// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 vite.config.ts，React 插件 + /api、/ws 代理至 localhost:8000

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

const API_TARGET = process.env.VITE_API_BASE_URL?.replace(/\/api\/v1\/?$/, "") ?? "http://localhost:8000";
const WS_TARGET = API_TARGET.replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: WS_TARGET,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: [],
  },
});
