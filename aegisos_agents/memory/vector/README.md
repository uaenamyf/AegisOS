# aegisos_agents/memory/vector — 向量存储

> 记忆子系统的 `向量存储` 子模块（隶属 aegisos_agents/ 智能体域）。开发前阅读 `aegisos_agents/memory/AGENT.md` 与 `developer/specs/08_AGENT_SPEC.md`。

## 职责
嵌入索引与相似度检索：支撑记忆的多路召回。

## 接口契约
统一通过 `protocol/memory.py` 的 `MemoryPacket` 读写，禁止子模块自造结构。

## 输入
- 来自上游模块的 `MemoryPacket`（working/semantic/episodic/archive/embedding/summary/compression 字段）。

## 输出
- 检索结果、压缩摘要、同步状态等，封装为 `MemoryPacket` 或 `Event(MemoryUpdate)`。

## 依赖
- `protocol/`、`tooling/configs/` 索引与淘汰策略配置。

## 测试
`pytest tests/aegisos_agents/memory/vector/`。
