# frontend/ 模块实现文档

> 表现层 — React + Vite 5.4 + Zustand + TypeScript，Controller-Service-Mapper 模式 + 5 视图。

📁 模块规范：[`AGENT.md`](AGENT.md) · 前后端计划：[`13_FRONTEND_BACKEND_PLAN.md`](../developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md)

---

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18 | UI 框架 |
| Vite | 5.4.21 | 构建 + HMR |
| Zustand | 4.5 | 全局状态管理 |
| TypeScript | 5.6 | 类型安全 |

---

## 架构

```
frontend/
├── src/
│   ├── protocol/         类型定义（自动生成 + 前端专用）
│   │   ├── types.ts         ← gen_ts_types.py 从 protocol/*.py 生成（36 个类型）
│   │   └── frontend-types.ts   ViewName · 路由类型
│   ├── mappers/
│   │   ├── store/           Zustand 全局状态
│   │   ├── apimappers/      API 客户端
│   │   ├── components/     共享组件
│   │   ├── viewmodels/      视图模型
│   │   ├── styles/          样式
│   │   └── utils/           工具函数
├── controllers/           交互控制层
│   ├── interaction.ts      用户交互控制
│   ├── events.ts           事件控制（SSE/WS）
│   └── routes.ts           路由定义（5 个 ViewName）
├── services/              服务层
│   ├── api/                REST API 封装
│   │   ├── agents.ts       Agent API（list / invoke）
│   │   ├── sessions.ts     Session API（create / list）
│   │   ├── tasks.ts        Task API（create / cancel）
│   │   ├── memory.ts      Memory API（read / write）
│   │   └── graph.ts        Graph API（get）
│   ├── graph/              图数据服务
│   ├── realtime/           实时通信
│   │   ├── sse.ts          SSE 处理器
│   │   └── ws.ts           WebSocket 处理器
│   └── session/            会话管理
└── views/                 视图
    ├── chat/               ✅ 完整实现
    ├── canvas/             🔲 占位
    ├── graph/              🔲 占位
    ├── monitor/            🔲 占位
    ├── replay/             🔲 占位
    └── layout/             布局组件
```

---

## 已实现

### 类型系统

| 文件 | 内容 | 来源 |
|------|------|------|
| [`src/protocol/types.ts`](src/protocol/types.ts) | 36 个 TS 类型：`Agent` · `Event` · `Graph` · `Task` · `MemoryPacket` · `ToolCall` · ... | 自动生成 |
| `src/protocol/frontend-types.ts` | `ViewName = 'chat' \| 'canvas' \| 'graph' \| 'monitor' \| 'replay'` | 手写 |

> 生成命令：`python3 tooling/scripts/gen_ts_types.py` 或 `npm run gen:types`

### 全局状态（Zustand）

| 文件 | Store 字段 |
|------|-----------|
| [`mappers/store/index.ts`](src/mappers/store/index.ts) | `currentSession` · `agents` · `selectedAgentId` · `chatMessages` · `isSending` · `graphData` |

**ChatMessage 类型**：`id` · `role`(user/agent) · `content` · `agentId` · `taskId` · `status`

### API 客户端

| 文件 | 功能 |
|------|------|
| [`mappers/apimappers/client.ts`](src/mappers/apimappers/client.ts) | 统一 HTTP 客户端：baseURL(`http://localhost:8000`) + `X-API-Key: aegis-dev-key` header + 错误处理 |

### REST API 服务

| 文件 | 方法 |
|------|------|
| [`services/api/agents.ts`](src/services/api/agents.ts) | `agentApi.list()` · `agentApi.invoke(id, input)` |
| [`services/api/sessions.ts`](src/services/api/sessions.ts) | `sessionApi.create()` · `sessionApi.list()` |
| [`services/api/tasks.ts`](src/services/api/tasks.ts) | `taskApi.create(goal)` · `taskApi.cancel(id)` · `taskApi.list()` |
| [`services/api/memory.ts`](src/services/api/memory.ts) | `memoryApi.read(query)` · `memoryApi.write(packet)` |
| [`services/api/graph.ts`](src/services/api/graph.ts) | `graphApi.get()` |

### 实时通信

| 文件 | 协议 | 功能 |
|------|------|------|
| [`services/realtime/sse.ts`](src/services/realtime/sse.ts) | SSE | `SseHandler` 类型，订阅 `/api/v1/events/stream` |
| [`services/realtime/ws.ts`](src/services/realtime/ws.ts) | WebSocket | `WsHandler` 类型，连接 `ws://host/ws/v1/stream` |

### Controllers

| 文件 | 功能 |
|------|------|
| [`controllers/interaction.ts`](src/controllers/interaction.ts) | 用户交互控制：发送消息 → 调 API → 更新 store |
| [`controllers/events.ts`](src/controllers/events.ts) | 事件控制：SSE/WS 消息分发到 store |
| [`controllers/routes.ts`](src/controllers/routes.ts) | `ROUTES` 数组：5 个视图的 name/label/key |

### ChatView（✅ 完整实现）

[`views/chat/ChatView.tsx`](src/views/chat/ChatView.tsx) — 功能：

- **Agent 下拉选择**：从 store 获取 14 个 Agent 列表
- **消息发送**：输入框 → `interactionController` → `agentApi.invoke()`
- **任务创建**：可选创建 Task 并轮询状态
- **响应展示**：Agent 返回内容渲染为消息气泡
- **自动滚动**：新消息时自动滚动到底部
- **发送状态**：`isSending` 禁用输入框

---

## 5 视图状态

| 视图 | 路由 | 状态 | 说明 |
|------|------|------|------|
| **ChatView** | `chat` | ✅ 完整实现 | Agent 对话 + 任务提交 |
| CanvasView | `canvas` | 🔲 占位 | 攻击链 DAG 可视化（待 React Flow） |
| GraphView | `graph` | 🔲 占位 | 拓扑图可视化 |
| MonitorView | `monitor` | 🔲 占位 | 防御看板 |
| ReplayView | `replay` | 🔲 占位 | 时序回放 |

---

## 未实现

- 🔲 CanvasView：攻击链 DAG 可视化（需安装 `reactflow`）
- 🔲 MonitorView：防御看板（告警/响应状态）
- 🔲 ReplayView：时序回放
- 🔲 前端 cyber 类型（`protocol/cyber.py` 未映射到 TS）
- 🔲 GraphView：动态拓扑图交互
