"""Observability domain public API.

Other modules import from `observability.api` only — never from internal
inspect/measure/present. This achieves decoupling.
"""
from __future__ import annotations

from typing import Any, Protocol

from protocol import Event


class MonitorAPI(Protocol):
    def record_metric(self, name: str, value: float, tags: dict) -> None: ...
    def get_metrics(self, query: dict) -> list: ...
    def alert(self, rule_id: str, ctx: dict) -> None: ...


class TraceAPI(Protocol):
    def start_span(self, name: str) -> Any: ...
    def end_span(self, span: Any) -> None: ...


class ReplayAPI(Protocol):
    def record_event(self, event: Event) -> None: ...
    def replay(self, session_id: str) -> list: ...


class BenchmarkAPI(Protocol):
    def run_suite(self, suite_id: str) -> dict: ...
    def get_results(self, suite_id: str) -> dict: ...


class EvaluationAPI(Protocol):
    def evaluate(self, run_id: str) -> dict: ...
    def get_report(self, run_id: str) -> dict: ...


class VisualizationAPI(Protocol):
    def render(self, data: dict, view: str = "default") -> Any: ...


__all__ = [
    "MonitorAPI", "TraceAPI", "ReplayAPI",
    "BenchmarkAPI", "EvaluationAPI", "VisualizationAPI",
]
