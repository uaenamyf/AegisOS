# Frontend/Mappers 映射器层 — AGENT.md

> 本文件是 `frontend/mappers/` 的开发规范，隶属 `frontend/` 域。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/ARCHITECTURE.md` 相关章节。

## 职责
映射器层：数据转换与共享能力。负责 protocol/ 类型 <-> 视图模型 <-> API 请求/响应转换，全局状态管理，共享工具函数，主题样式与静态资产。是前端数据与公共能力的关口。

## 读取目录（允许读）
- protocol/
- frontend/services/
- tooling/configs/
- developer/FRONTEND_GUIDE.md

## 禁止修改目录
- frontend/controllers/ 交互处理
- frontend/services/ 业务逻辑
- frontend/views/ UI 组件
- backend/
- protocol/ 类型定义
- agents/

## 输出
- frontend/mappers/viewmodels/ 视图模型（protocol -> VM 转换，供 views 消费）
- frontend/mappers/apimappers/ API 映射（请求/响应 <-> protocol 类型）
- frontend/mappers/store/ 全局状态管理
- frontend/mappers/utils/ 共享工具函数
- frontend/mappers/styles/ 主题与样式
- frontend/mappers/assets/ 静态资产

## 依赖
- protocol/ 契约（类型来源，生成 TS 类型）
- frontend/services/ 业务数据

## 接口
供 frontend/services/ 与 frontend/views/ 调用；封装数据转换与公共能力。

## 测试方式
`pytest tests/frontend/mappers/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/frontend/mappers/`（结构化 JSON 日志，按 session/task 切分）。

## Prompt 位置
`agents/tools/prompts/mappers/`（版本化管理，变更需经 agents/perception/reflection 评估）。

## 配置位置
`tooling/configs/mappers.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/CODING_RULES.md` 与 `developer/FRONTEND_GUIDE.md`。
- 所有数据结构使用 `protocol/` 类型生成的 TS 类型，禁止手写并行类型。
- 映射器只做数据转换与公共能力，不含业务逻辑。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 修改前确认本模块在分层中的位置（见 `developer/DIRECTORY_GUIDE.md`），不得越界。
