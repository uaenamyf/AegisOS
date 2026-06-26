# P4 — Scheduler

> AegisOS 系统级开发计划阶段 P4。Agent 开发前据此定位「现在做哪一步、下一步是什么」。

## 目标
实现调度器

## 输入
agents/planning/engine/router/ + 任务

## 输出
agents/planning/engine/scheduler/ 队列与策略

## 接口
schedule(task) -> execution

## 测试
调度/抢占/重试测试

## 风险
死锁/饥饿

## 完成标准
任务可按依赖与资源调度执行

## 依赖阶段
需 P3 完成
