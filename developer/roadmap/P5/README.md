# P5 — Planner + Agents

> AegisOS 系统级开发计划阶段 P5。Agent 开发前据此定位「现在做哪一步、下一步是什么」。

## 目标
实现规划器与各 Agent

## 输入
agents/planning/engine/scheduler/ + agents/memory/

## 输出
agents/planning/engine/planner/ + agents/* + agents/tools/runtime/

## 接口
plan(goal) / receive()->...->respond()

## 测试
规划与 Agent 端到端测试

## 风险
计划质量与 Agent 协作稳定性

## 完成标准
Agent 群体可完成端到端任务

## 依赖阶段
需 P4 完成
