"""Frontend domain public API.

Exposes UI component registration, view rendering, and interaction
hooks for plugin/extension integration. Other modules (e.g. observability
visualization) import from `frontend.api` only.
"""
from __future__ import annotations

from typing import Any, Protocol


class ViewAPI(Protocol):
    def render_view(self, view_name: str, data: dict) -> Any: ...
    def register_view(self, name: str, component: Any) -> None: ...


class InteractionAPI(Protocol):
    def on_interaction(self, event_name: str, handler) -> None: ...
    def dispatch_interaction(self, event_name: str, payload: dict) -> None: ...


class ThemeAPI(Protocol):
    def set_theme(self, theme: str) -> None: ...
    def get_theme(self) -> str: ...


__all__ = ["ViewAPI", "InteractionAPI", "ThemeAPI"]
