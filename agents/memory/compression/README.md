# agents/memory/compression — 记忆压缩

> 记忆子系统的 `记忆压缩` 子模块（隶属 agents/ 智能体域）。开发前阅读 `agents/memory/AGENT.md` 与 `developer/specs/08_AGENT_SPEC.md`。

## 职责
摘要与上下文压缩：在 Token 预算内保留关键信息。

## 接口契约
统一通过 `protocol/memory.py` 的 `MemoryPacket` 读写，禁止子模块自造结构。

## 输入
- 来自上游模块的 `MemoryPacket`（working/semantic/episodic/archive/embedding/summary/compression 字段）。

## 输出
- 检索结果、压缩摘要、同步状态等，封装为 `MemoryPacket` 或 `Event(MemoryUpdate)`。

## 依赖
- `protocol/`、`tooling/configs/` 索引与淘汰策略配置。

## 测试
`pytest tests/agents/memory/compression/`。
