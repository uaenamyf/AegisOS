# Tooling/API 公共接口 — AGENT.md

> 本文件是 `tooling/api/` 的开发规范，隶属 `tooling/` 域。这是**该域对外的唯一公共接口**，其他模块通过本接口调用本域能力，实现解耦。

## 职责
工程支撑域公共 API：对其他模块暴露配置加载/读写、脚本运行等接口。其他模块只通过 `tooling.api` 导入，不直接访问 tooling/configs|scripts 内部实现。

## 解耦原则
- **其他模块只导入 `from tooling.api import ...`**，禁止直接访问 `tooling/` 内部子包。
- 内部实现可自由重构，只要 `api/` 接口签名不变，依赖方不受影响。
- 接口参数与返回值一律使用 `protocol/` 定义的类型。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- tooling/ 内部实现（configs/scripts）
- frontend/
- backend/
- agents/
- protocol/ 类型定义

## 输出
- tooling/api/__init__.py 公共 Protocol 接口
- ConfigAPI / ScriptAPI

## 依赖
- protocol/ 契约
- developer/ 规范

## 接口
其他模块 `from tooling.api import ConfigAPI` 等接口；实现由 tooling/ 内部注入。

## 暴露的接口清单
ConfigAPI(加载/获取/设置配置) · ScriptAPI(运行/列出脚本)

## 测试方式
`pytest tests/tooling/api/`，验证接口契约与 mock 兼容性，覆盖率目标 >= 80%。

## 日志位置
`logs/tooling/api/`（结构化 JSON 日志，按 session/task 切分）。

## 配置位置
`tooling/configs/tooling_api.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 接口参数/返回值必须复用 `protocol/` 类型，禁止自造并行结构。
- 接口签名变更属于**破坏性变更**，需在 `developer/CHANGELOG.md` 标注并通知所有依赖方。
- 新增接口需同步更新 `developer/specs/05_API_SPEC.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/09_DEVELOPMENT_SPEC.md
- **API 边界**：tooling/api/ — from tooling.api import ...
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（靶场编排/评测脚本）
