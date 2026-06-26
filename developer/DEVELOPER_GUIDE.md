# DEVELOPER_GUIDE.md — AI 如何开发本仓库

> 本文件规定 AI Agent 开发 AegisOS 的标准流程，确保高效且不越界。

## 核心原则
Agent 永不扫描整个项目；按模块边界精准读写。

## 标准开发流程
```
Developer Agent
  -> 读取 developer/（AGENT.md 总规范 + ARCHITECTURE + ROADMAP）
  -> 读取 developer/roadmap/ 定位当前阶段
  -> 定位目标模块
  -> 读取该模块 AGENT.md（职责/读取目录/禁止修改目录/接口）
  -> 读取 protocol/ 相关契约
  -> 读取 tooling/configs/ 相关配置
  -> 生成代码
  -> 运行 tests/{module}/
  -> 生成/更新 docs 与 CHANGELOG
  -> commit
```

## 边界纪律
- 严格遵守目标模块 AGENT.md 的「禁止修改目录」。
- 跨模块需求：先改 protocol/ 契约（若必要）并通知相关模块，不在本模块内越界实现。

## 质量门禁
- 提交前：`ruff format && ruff check --fix && mypy && pytest tests/{module}/`。
- 接口变更同步更新 API_SPEC/EVENT_SPEC 与 CHANGELOG。

## 新增模块
- 创建目录 + AGENT.md（填写 10 项字段）+ 注册到 DIRECTORY_GUIDE + 在 ROADMAP 标注阶段。

## 协作
- 多 Agent 协作经 orchestrator + router 动态路由；低熵稀疏通信。
