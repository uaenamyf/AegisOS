# P3 — Router

> AegisOS 系统级开发计划阶段 P3。Agent 开发前据此定位「现在做哪一步、下一步是什么」。

## 目标
实现动态图路由

## 输入
protocol/ + agents/planning/engine/topology/

## 输出
agents/planning/engine/router/ 动态图与低熵路由

## 接口
route(task) -> Route

## 测试
路由决策与图更新测试

## 风险
动态图一致性

## 完成标准
动态路由可计算并产出稀疏通信链

## 依赖阶段
需 P2 完成
