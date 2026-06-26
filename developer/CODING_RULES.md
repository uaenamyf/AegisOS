# CODING_RULES.md — 编码规则

> 全仓库统一编码规则，AI 与人类开发者共同遵守。

## 通用
1. 契约先行：跨模块数据结构复用 `protocol/`，禁止自造并行结构。
2. 通信走 Message 信封，禁止裸 JSON 跨模块传递。
3. 修改任一模块前先读其 `AGENT.md`，不得越界「禁止修改目录」。
4. 不提交密钥/凭据；配置走 `tooling/configs/environments/`。
5. 日志不记录敏感载荷（脱敏）。
6. 不添加无关注释；意图由测试与命名表达。
7. 新增接口同步更新 `API_SPEC.md` / `EVENT_SPEC.md`。
8. 提交前运行测试并更新 `CHANGELOG.md`。

## 命名
- 模块/包：snake_case；类：PascalCase；常量：UPPER_SNAKE。
- 协议类型与 `protocol/` 字段名一致。

## 结构
- 每个子系统对外暴露稳定接口，内部实现可重组。
- 公共能力下沉 agents/action/execution/tools/ / data/models/，避免重复实现。

## 错误处理
- 显式异常类型，不吞异常；失败可重试/回滚的走 protocol Task 字段。
- 边界处校验输入（schema）。

## 测试
- 公共接口必有测试；bug 修复附回归测试。
- 覆盖率目标 >= 80%。

## 依赖
- 新增三方依赖需评估必要性，记录于部署文档。
