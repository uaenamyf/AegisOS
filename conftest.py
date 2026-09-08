# date: 2026-09-04
# dev: OpenSquilla
# changelog: R7 强制测试走 Mock——防止加载 tooling/configs/.env 后真实 API Key
#            污染测试环境（_load_dotenv 不覆盖已有环境变量，此处先设即生效）
"""Pytest 根配置：确保仓库根在 sys.path 中（工作区源码优先）。

R7 起强制 ``AEGIS_USE_MOCK=true``：真实 Key 写入 ``tooling/configs/.env`` 后，
pytest 加载 settings 时会读到 ``OPENAI_API_KEY``；若不强制 mock，现有
624 个依赖 Mock 行为的测试会误走真实 API（慢、花钱、不可重复）。
"""

import os

os.environ["AEGIS_USE_MOCK"] = "true"
# R7: 中和 .env 里的 OPENAI_AGENTS_DISABLE_TRACING=true。
# SDK DefaultTraceProvider 首次使用时懒读该变量并缓存；组合跑时
# tests/backend 先加载 settings → .env 的 true 会全局禁用 tracing，
# 导致 test_cyber_tracing.py 的 *_traced 测试 trace_data 为 None。
# 此处先设为 "false"（_load_dotenv 不覆盖已有变量），保住 tracing 采集。
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "false"

# R7: 清除 SDK 默认 trace 导出器（BatchTraceProcessor）。
# 不能用 set_tracing_disabled(True)——那会连 CyberOrchestrator 的
# tracing processor 采集一起禁用，导致 test_cyber_tracing.py 失败。
# set_trace_processors([]) 只移除默认导出器（无 Key 时的 stderr 噪音），
# 保留自定义 processor 机制（enable_tracing() 会重新设置自己的 processor）。
from agents import set_trace_processors

set_trace_processors([])
