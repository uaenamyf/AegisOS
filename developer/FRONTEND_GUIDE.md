# FRONTEND_GUIDE.md — 前端规范

> AI Native IDE 前端位于 `frontend/`，采用与后端对称的 **Controller-Service-Mapper** 三层架构 + Views 视图层。

## 技术栈
- 框架：React + TypeScript；状态：轻量 store；构建：Vite。
- 图谱渲染：WebGL/Canvas（动态异构图大规模节点）。
- 实时：WebSocket（双向）+ SSE（事件流）。

## 架构
```
用户交互/后端事件 -> frontend/controllers/（交互处理/事件分发，不含业务逻辑）
  -> frontend/services/（API 调用/WS·SSE 管理/状态编排）
  -> frontend/mappers/（数据转换/视图模型构建/全局状态/共享工具）
  -> frontend/views/（UI 渲染：canvas/graph/monitor/replay）
```

## 结构
### frontend/controllers/ 控制器
- `interaction/` 用户交互控制器（画布操作/图谱交互/监控筛选/回放控制）
- `events/` 后端事件控制器（WS/SSE 事件分发）
- `routes/` 前端路由（页面/视图切换）
- 只做交互/事件处理 + 调 service + 分发到 views，**不含业务逻辑**。

### frontend/services/ 服务
- `api/` API 调用服务（REST 请求封装，经 backend/gateway）
- `realtime/` 实时服务（WebSocket/SSE 连接管理与消息分发）
- `session/` 会话服务（会话状态、任务状态）
- `graph/` 动态图服务（图数据获取与更新订阅）
- 业务逻辑核心：API 调用、实时连接管理、状态编排。

### frontend/mappers/ 映射器
- `viewmodels/` 视图模型（protocol -> VM 转换，供 views 消费）
- `apimappers/` API 映射（请求/响应 <-> protocol 类型）
- `store/` 全局状态管理 · `utils/` 共享工具函数 · `styles/` 主题与样式 · `assets/` 静态资产
- 数据转换与公共能力，不含业务逻辑。

### frontend/views/ 视图（按功能特性）
- `canvas/` 任务编排画布（DAG 编辑/运行）
- `graph/` 动态图可视化（WebGL/Canvas 大规模增量渲染）
- `monitor/` Agent 状态监控面板（实时指标、告警）
- `replay/` 回放时间线（事件流确定性回放、播放控制）

## 约定
- 所有数据结构使用 `protocol/` 类型生成的 TS 类型，禁止手写并行类型。
- API 调用统一经 backend/gateway，类型由 `developer/API_SPEC.md` 生成。
- 控制器不写业务逻辑；业务走 services/，数据转换走 mappers/，渲染走 views/。
- 大图：增量渲染 + 视口剔除 + LOD；实时：节流/批量更新。
- 支持暗色主题；关键操作有键盘可达路径。
