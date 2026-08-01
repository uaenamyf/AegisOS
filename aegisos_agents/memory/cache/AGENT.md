# Agents/Memory/Cache — AGENT.md

> 本文件是 `aegisos_agents/memory/cache/` 模块的开发规范。

## 职责
二级记忆缓存：L1 查询缓存（TTL 60s）+ L2 热点缓存（LRU 100 条，访问 ≥3 次自动晋升）。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `store.py` — MemoryCache

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`get_query(key)` / `set_query(key, results, ttl)` / `get_hot(task_id)` / `touch(task_id)` / `invalidate(task_id)` / `stats()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_cache.py`
