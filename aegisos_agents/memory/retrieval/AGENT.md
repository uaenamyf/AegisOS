# Agents/Memory/Retrieval — AGENT.md

> 本文件是 `aegisos_agents/memory/retrieval/` 模块的开发规范。

## 职责
混合检索引擎：向量（余弦相似度）+ 关键词（子串匹配）+ 图（ATT&CK 关联）三通道 RRF 融合检索。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/vector/
- aegisos_agents/memory/semantic/
- aegisos_agents/memory/episodic/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `engine.py` — RetrievalEngine + ScoredPacket

## 依赖
- protocol/memory.py MemoryPacket
- aegisos_agents/memory/vector/store.py VectorMemory（只读）
- aegisos_agents/memory/semantic/store.py SemanticMemory（只读）
- aegisos_agents/memory/episodic/store.py EpisodicMemory（只读）

## 接口
`retrieve(query, query_embedding, channels, top_k) -> list[ScoredPacket]`

## 测试方式
`pytest tests/aegisos_agents/memory/test_retrieval.py`

## H2 升级路径
图通道当前基于 SemanticMemory 字典关联；H2 后可替换为 Neo4j ATT&CK 图遍历。
