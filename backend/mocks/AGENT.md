# Backend/Mocks 模拟层 — AGENT.md

> 本文件是 `backend/mocks/` 的开发规范，隶属 `backend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
模拟层：agents.api 端口的 mock 实现。为开发/测试模式提供轻量替代，无需启动完整 Agent Runtime 即可运行后端。

## 读取目录（允许读）
- agents/api/
- protocol/
- agents/tools/llms/mock_provider.py
- developer/specs/10_INTERFACE_BOUNDARY_SPEC.md

## 禁止修改目录
- backend/routers/（路由层）
- backend/services/（服务层）
- backend/repositories/（仓储层）
- backend/models/（ORM 实体）
- backend/core/（组合根）
- protocol/
- developer/
- frontend/
- agents/（只读 agents/api/ + agents/tools/llms/mock_provider.py）

## 输出
- mocks/agent_registry.py — MockAgentRegistry（Agent 注册/查询，含赛题 Agent 规格）
- mocks/runtime.py — MockRuntime（任务提交/执行，含攻防调度映射）
- mocks/cyber_provider.py — _CyberMockProvider（攻防场景 mock 响应生成）
- mocks/memory.py — MockMemoryAPI（记忆读写）
- mocks/execution.py — MockExecutionAPI（工具执行）
- mocks/event_bus.py — MockEventBusAPI（事件发布/订阅）
- mocks/__init__.py — barrel 导出全部 Mock 类

## 依赖
- agents/api/ — 端口接口定义（Protocol）
- protocol/ — 数据契约类型（Task / ToolCall / MemoryPacket / Event 等）
- agents/tools/llms/mock_provider.py — MockLLMProvider（提供 responses property）

## 接口
- MockAgentRegistry: 实现 AgentRegistryAPI 端口
- MockRuntime: 实现 RuntimeAPI 端口
- MockMemoryAPI: 实现 MemoryAPI 端口
- MockExecutionAPI: 实现 ExecutionAPI 端口
- MockEventBusAPI: 实现 EventBusAPI 端口

## 测试方式
`pytest tests/backend/`，覆盖 mock 行为正确性、攻防场景响应。

## 交叉引用（去哪里找）
- **本域根规范**：backend/AGENT.md
- **接口边界**：developer/specs/10_INTERFACE_BOUNDARY_SPEC.md
- **组合根**：backend/core/composition.py（DI 装配，注入 mock 实例）
- **端口定义**：agents/api/ports.py（Protocol 接口）
- **LLM Mock**：agents/tools/llms/mock_provider.py（底层 mock LLM）
