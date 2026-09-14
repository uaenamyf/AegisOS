# XH-202631 真实 API 评估记录

运行模式：`real`
Provider：`ark`
Model：`ark-code-latest`
API 用例：`9/9`
API 成功率：`100%`
普通 Chat 成功率：`100%`
演练意图安全拦截：`通过`

## 用例结果

| 用例 | 状态 | HTTP | 延迟 ms |
|---|---:|---:|---:|
| health | 通过 | 200 | 215.66 |
| runtime_mode | 通过 | 200 | 23.69 |
| infra_nodes | 通过 | 200 | 23.11 |
| chat_natural_language | 通过 | 200 | 27913.21 |
| chat_system_status | 通过 | 200 | 71253.40 |
| drill_intent_safety_gate | 通过 | 200 | 10.35 |
| memory_session_read | 通过 | 200 | 10.94 |
| graph_read | 通过 | 200 | 15.12 |
| drill_history | 通过 | 200 | 937.52 |

## 限制

- 本评估通过真实 AegisOS API 和 ARK Provider。
- 真实多轮 Drill 结果使用综合报告中的受控记录，不在脚本中重复消耗模型调用。
