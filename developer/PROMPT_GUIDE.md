# PROMPT_GUIDE.md — Prompt 规范

> 所有 Prompt 模板存放 `agents/tools/prompts/`，版本化管理。

## 位置约定
- 模块模板：`agents/tools/prompts/{module}/`
- Agent 模板：`agents/tools/prompts/agents/{agent}/`
- 全局库：`agents/tools/prompts/library/`；版本：`agents/tools/prompts/versions/`

## 模板要求
- 变量显式声明并校验；渲染失败抛错而非静默。
- 角色、任务、约束、输出格式分段清晰。
- 输出格式优先结构化（JSON Schema），便于 protocol 解析。

## 版本与评估
- 每次变更生成新版本，旧版本保留。
- 变更需经 reflection 评估（质量/成本/失败率）。
- 支持 A/B：同任务多版本并行对比。

## 调用
- 通过 `agents/tools/prompts/` 模块 `render(template, vars) -> prompt` 渲染。
- 渲染结果作为 `protocol/` Payload 投递给 agents/tools/llms/。
- 禁止在业务代码中内联大段 Prompt 字符串。

## 安全
- 用户输入注入变量需转义/围栏隔离。
- Prompt 不含密钥。
