"""Data domain public API.

Other modules import from `data.api` only — never from internal
datasets/models. This achieves decoupling.
"""

from __future__ import annotations

from typing import Any, Protocol


class DatasetAPI(Protocol):
    def load(self, name: str, version: str = "latest") -> Any: ...
    def list_datasets(self) -> list: ...
    def preprocess(self, name: str, config: dict) -> Any: ...


class ModelSchemaAPI(Protocol):
    def register_schema(self, name: str, schema: dict) -> None: ...
    def validate(self, name: str, data: dict) -> bool: ...
    def get_schema(self, name: str) -> dict: ...
    def migrate(self, name: str, from_ver: str, to_ver: str) -> Any: ...


__all__ = ["DatasetAPI", "ModelSchemaAPI"]
