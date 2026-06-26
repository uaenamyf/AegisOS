# TOOL_SPEC.md — 工具规范

> 工具统一注册于 `agents/action/execution/tools/`，经 `agents/action/execution/executor/` 沙箱执行。

## 工具协议
- 调用：`protocol/tool.py` 的 `ToolCall(name, args, timeout)`。
- 返回：`ToolResult(ok, output, error, meta)`。
- 规格：`agents/action/execution/tools/specs/` 中以 schema 声明参数/输出/权限/资源限制。

## 注册
- `agents/action/execution/tools/registry/` 维护名称->实现映射；启动时加载 `agents/action/execution/tools/builtin/`。
- 第三方工具走 `agents/action/execution/tools/wrappers/` 适配统一协议。

## 执行
- 一律经 `agents/action/execution/executor/`：沙箱隔离、超时、资源限制、副作用采集。
- 危险操作（文件/网络/代码执行）需显式权限配置（tooling/configs/）。

## 权限
- 按 Agent 角色授予可调用工具白名单（tooling/configs/agents/）。
- 拒绝越权调用并记录事件。

## 可观测
- 每次调用产出 ToolCall/ToolFinish 事件（EVENT_SPEC）。
- 失败可重试的由调度器决定。
