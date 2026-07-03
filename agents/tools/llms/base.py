# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 多模型兼容层抽象接口
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMRequest:
    prompt: str
    model_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    stop: list = field(default_factory=list)


@dataclass
class LLMResponse:
    text: str = ""
    ok: bool = True
    error: str = ""
    usage: dict = field(default_factory=dict)
    model_id: str = ""


class ModelProvider(Protocol):
    """Unified interface for all LLM providers."""

    def complete(self, request: LLMRequest) -> LLMResponse: ...
