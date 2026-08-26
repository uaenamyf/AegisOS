# date: 2026-08-26
# dev: ox-alpha
# changelog: R1 新增——置于仓库根使 pytest 将仓库根加入 sys.path，
#            保证测试可直接 import 工作区源码（而非仅依赖 editable 安装快照）
"""Pytest 根配置：确保仓库根在 sys.path 中（工作区源码优先）。"""
