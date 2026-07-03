"""Tooling domain public API.

Other modules import from `tooling.api` only — never from internal
configs/scripts. This achieves decoupling.
"""

from __future__ import annotations

from typing import Any, Protocol


class ConfigAPI(Protocol):
    def load(self, env: str = "dev") -> dict: ...
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...


class ScriptAPI(Protocol):
    def run(self, name: str, args: dict) -> dict: ...
    def list_scripts(self) -> list: ...


__all__ = ["ConfigAPI", "ScriptAPI"]
