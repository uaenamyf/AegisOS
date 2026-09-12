# Backend/Services 服务层 — AGENT.md

> 本文件是 `backend/services/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
服务层：业务逻辑核心。用例编排（会话管理、任务下发、Agent 编排），事务管理，调用 aegisos_agents/ 子系统与 backend/repositories/。控制器与持久化之间的业务中枢。

## 读取目录（允许读）
- backend/repositories/
- backend/models/
- backend/core/
- aegisos_agents/api/
- aegisos_agents/planning/engine/
- protocol/
- tooling/configs/
- developer/specs/05_API_SPEC.md
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- backend/routers/（路由层）
- backend/models/（ORM 实体定义）
- backend/repositories/（数据访问实现）
- backend/core/（组合根/鉴权/中间件）
- protocol/
- developer/
- frontend/
- aegisos_agents/（只经 aegisos_agents/api/ 调用）

## 输出
- services/session_service.py — 会话管理（创建/查询/关闭）
- services/task_service.py — 任务管理（创建/查询/状态流转）
- services/agent_service.py — Agent 编排（调用/查询/控制）
- services/memory_service.py — 记忆网关（桥接 aegisos_agents.api.MemoryAPI）
- services/graph_service.py — 动态图查询
- services/di_ports.py — 依赖注入端口定义（Protocol 接口，供 core/composition.py 实现）
- services/__init__.py — barrel 导出

## 依赖
- backend/repositories/ — 数据持久化
- backend/models/converters.py — protocol↔Entity 转换
- backend/core/composition.py — DI 注入
- aegisos_agents/api/ — 智能体域公共接口（AgentRegistry/Runtime/Memory/Execution/EventBus）
- protocol/ — 数据契约

## 接口
- SessionService / TaskService / AgentService / MemoryService / GraphService
- DI 端口 Protocol（供 core/composition.py 提供实现）

## 测试方式
`pytest tests/backend/`，覆盖核心业务路径、事务回滚、异常边界。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **API 契约**：developer/specs/05_API_SPEC.md
- **接口边界**：developer/specs/10_INTERFACE_BOUNDARY_SPEC.md
- **仓储层**：backend/repositories/（数据访问）
- **模型层**：backend/models/（ORM 实体 + 转换器）
- **组合根**：backend/core/composition.py（DI 装配）
- **Agent 域**：aegisos_agents/api/（公共接口）
