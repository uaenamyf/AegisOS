# date: 2026-09-04
# dev: OpenSquilla
# changelog: R7 新建——运行时模式管理器（mock/real 双编排器懒缓存 + 即时切换）
"""运行时模式管理：控制攻防编排器走 Mock Provider 还是真实 LLM API。

设计要点：
- 进程内单例；``get_orchestrator()`` 按当前模式懒创建并缓存两个编排器
  （mock 与 real 各一个），切换模式只换引用、不重建 11 个 Agent。
- 默认模式：显式 ``AEGIS_USE_MOCK=true`` → mock；否则有 ``OPENAI_API_KEY``
  → real（默认真实 LLM）；否则回落 mock（本地/评委无 Key 不崩溃）。
- ``describe()`` 供前端徽标展示（模式/模型/提供商/是否有 Key）。
"""

from __future__ import annotations

import os
import threading

# 避免循环导入：编排器类型仅用于类型注解（TYPE_CHECKING）
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

_MODE_MOCK = "mock"
_MODE_REAL = "real"
_VALID_MODES = (_MODE_MOCK, _MODE_REAL)

_lock = threading.Lock()
_current: str = "mock"
_orchestrators: dict[str, Any] = {}


def _default_mode() -> str:
    """根据环境变量决定初始模式（默认真实 LLM，有 Key 时）。"""
    flag = os.getenv("AEGIS_USE_MOCK", "").lower()
    if flag in ("1", "true", "yes"):
        return _MODE_MOCK
    if os.getenv("OPENAI_API_KEY"):
        return _MODE_REAL
    return _MODE_MOCK


def _build(mode: str) -> Any:
    """按模式构建编排器（mock=预置响应表；real=SDK 真实模型）。"""
    if mode == _MODE_MOCK:
        from aegisos_agents.planning.orchestrator import CyberOrchestrator
        from backend.mocks.cyber_provider import _CyberMockProvider

        return CyberOrchestrator(mock=_CyberMockProvider())

    from aegisos_agents.planning.orchestrator import CyberOrchestrator
    from aegisos_agents.tools.llms.sdk_provider import SDKProvider

    provider = SDKProvider()
    model = provider.get_sdk_model()
    return CyberOrchestrator(model=model)


def init() -> None:
    """初始化当前模式（进程启动时调用一次）。"""
    global _current
    with _lock:
        _current = _default_mode()


def get_mode() -> str:
    """返回当前模式（``"mock"`` / ``"real"``）。"""
    return _current


def set_mode(mode: str) -> None:
    """切换模式；``real`` 模式要求已配置 ``OPENAI_API_KEY``。

    Raises:
        ValueError: 模式非法，或 real 模式缺少 API Key。
    """
    global _current
    if mode not in _VALID_MODES:
        raise ValueError(f"invalid mode: {mode!r} (expected {_VALID_MODES})")
    if mode == _MODE_REAL and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("real mode requires OPENAI_API_KEY")
    with _lock:
        _current = mode
        # 同步环境变量：SDKProvider / MockProvider 均读 AEGIS_USE_MOCK 决定内部行为，
        # 不同步会导致 real 模式构建时 SDKProvider 仍按 mock 初始化而报错（实测 500）。
        os.environ["AEGIS_USE_MOCK"] = "true" if mode == _MODE_MOCK else "false"


def get_orchestrator() -> Any:
    """返回当前模式对应的编排器（懒创建 + 缓存）。"""
    global _current
    with _lock:
        mode = _current
        orch = _orchestrators.get(mode)
        if orch is None:
            orch = _build(mode)
            _orchestrators[mode] = orch
        return orch


def invalidate(mode: str | None = None) -> None:
    """丢弃缓存的编排器（换 API Key / 换模型后强制重建）。

    Args:
        mode: 指定丢弃某模式的编排器；None 时全部丢弃。
    """
    global _orchestrators
    with _lock:
        if mode is None:
            _orchestrators.clear()
        else:
            _orchestrators.pop(mode, None)


def describe() -> dict[str, Any]:
    """返回模式描述，供前端徽标渲染。

    Returns:
        ``{mode, model, provider, has_key, available}``。
    """
    model = os.getenv("OPENAI_DEFAULT_MODEL", "")
    base_url = os.getenv("OPENAI_BASE_URL", "") or ""
    # 从 base_url 推断提供商（deepseek / ark / openai / custom）
    host = base_url.split("//")[-1].split("/")[0] if base_url else ""
    if "deepseek" in host:
        provider = "deepseek"
    elif "ark" in host or "volces" in host:
        provider = "ark"
    elif not host:
        provider = "openai"
    else:
        provider = host.split(".")[0] or "openai"
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "mode": _current,
        "model": model,
        "provider": provider,
        "has_key": has_key,
        "available": [_MODE_MOCK, _MODE_REAL] if has_key else [_MODE_MOCK],
    }
