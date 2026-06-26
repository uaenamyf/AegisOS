# P1 — Protocol

> AegisOS 系统级开发计划阶段 P1。Agent 开发前据此定位「现在做哪一步、下一步是什么」。

## 目标
定义全系统通信协议

## 输入
协议设计（developer/MESSAGE_PROTOCOL.md）

## 输出
protocol/*.py 数据类 + 序列化

## 接口
Message/Event/Task/Memory/Heartbeat/Graph/Tool/Sync

## 测试
协议序列化往返测试

## 风险
格式频繁变更导致全局返工

## 完成标准
协议可序列化往返且 schema 校验通过

## 依赖阶段
需 P0 完成
