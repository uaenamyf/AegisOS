# date: 2026-07-06
# dev: myf
# changelog: 新建 eventbus 包——导出 EventBus 实现
"""事件总线包 —— 发布/订阅事件总线实现。

导出 :class:`EventBus`，供 planning 域各子模块解耦通信。
详见 ``impl.py`` 模块文档。
"""
from .impl import HISTORY_LIMIT, EventBus

__all__ = ["EventBus", "HISTORY_LIMIT"]
