# Agents/Memory/Reflection — AGENT.md

> 本文件是 `aegisos_agents/memory/reflection/` 模块的开发规范。

## 职责
反思引擎：对决策类记忆做三维评估（时效性 × 引用频次 × 结果标记），纯算法实现，用于 recall 结果重排序。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `engine.py` — ReflectionEngine

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`evaluate(packet)` / `rank(memories)` / `tag_outcome(task_id, outcome)` / `record_reference(task_id)` / `get_reference_count(task_id)` / `is_cold(task_id, threshold)` / `stats()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_reflection.py`
