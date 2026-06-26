# MEMORY_GUIDE.md — 记忆子系统规范

> 记忆子系统位于 `agents/memory/`，是一个完整子系统（12 子模块）。统一接口为 `protocol/memory.py` 的 `MemoryPacket`。

## 分层
| 子模块 | 类型 | 生命周期 | 说明 |
|--------|------|----------|------|
| working | 工作记忆 | 短时 | 当前任务上下文/变量 |
| episodic | 情景记忆 | 中长期 | 事件序列/执行记录 |
| semantic | 语义记忆 | 长期 | 知识/概念/事实 |
| vector | 向量存储 | 长期 | 嵌入索引/相似度 |
| archive | 归档 | 冷 | 历史快照/淘汰 |
| compression | 压缩 | - | 摘要/Token 预算裁剪 |
| retrieval | 检索 | - | 多路召回+重排序 |
| reflection | 反思 | 长期 | 经验/失败模式 |
| checkpoint | 检查点 | - | 状态保存/恢复 |
| cache | 缓存 | 短时 | 高频访问 |
| snapshot | 快照 | - | 系统状态快照 |
| sync | 同步 | - | 端边云一致性 |

## 接口
- `read(query) -> MemoryPacket`
- `write(packet) -> ack`
- `retrieve(query) -> hits`（经 retrieval 多路召回）

## 写入流程
```
数据 -> compression 压缩 -> 分流(working/semantic/episodic/archive)
  -> vector 索引 -> reflection 抽取经验 -> cache 更新 -> sync 同步
```

## 读取流程
```
query -> retrieval(向量+关键词+图) -> 重排序 -> 组装 MemoryPacket -> 返回
```

## 容错
- checkpoint/snapshot 支持恢复；sync 断连续传。
- 写入幂等（基于 packet id）。

## 评估
- 记忆质量（检索命中、压缩信息保留率）由 observability/measure/evaluation/ 度量。
