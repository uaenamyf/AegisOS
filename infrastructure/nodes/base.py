# date: 2026-08-26
# dev: ox-alpha
"""节点 HTTP 底座 —— DeviceNode/EdgeNode 共用的请求与失败封装。

职责：
    - 统一 urllib POST/GET + JSON 编解码 + 超时注入；
    - 把 URLError/TimeoutError/HTTPError/json 异常翻译成 InferenceResult.failure，
      保证节点层"绝不向调度器抛网络异常"的契约（R6 降级链路依赖此语义）。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from infrastructure.nodes.descriptor import InferenceResult, NodeProfile


class BaseHttpNode:
    """三层节点的公共底座：持有档案 + 提供 JSON HTTP 访问与异常翻译。"""

    def __init__(self, profile: NodeProfile) -> None:
        self.profile = profile

    @classmethod
    def from_profile(cls, profile: NodeProfile) -> BaseHttpNode:
        return cls(profile)

    # ---- 底层请求 ----

    def _post_json(
        self, path: str, payload: dict[str, Any], timeout_s: float, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """POST JSON 并解析响应；任何失败以异常形式抛给上层翻译。

        Args:
            path: URL 路径（拼接到 base_url 后）。
            payload: 序列化为 JSON 的请求体。
            timeout_s: 超时秒数。
            headers: 可选额外请求头（与 Content-Type 合并）。
        """
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(
            f"{self.profile.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=req_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            parsed: Any = json.loads(resp.read().decode("utf-8"))
            return dict(parsed)

    def _get_json(
        self, path: str, timeout_s: float, headers: dict[str, str] | None = None
    ) -> tuple[int, dict[str, Any]]:
        """GET 并返回 (status_code, body)；连接失败直接抛异常。

        Args:
            path: URL 路径（拼接到 base_url 后）。
            timeout_s: 超时秒数。
            headers: 可选额外请求头。
        """
        req_headers = headers or {}
        req = urllib.request.Request(
            f"{self.profile.base_url}{path}", headers=req_headers, method="GET"
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            try:
                body: Any = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                body = {}
            return resp.getcode(), body

    # ---- 异常翻译 ----

    def _describe_error(self, exc: Exception) -> str:
        """把网络异常翻译为简明错误串（含 HTTP 状态码）。"""
        if isinstance(exc, urllib.error.HTTPError):
            return f"http {exc.code}: {exc.reason}"
        if isinstance(exc, urllib.error.URLError):
            return f"connection failed: {exc.reason}"
        if isinstance(exc, TimeoutError):
            return f"timeout: {exc}"
        if isinstance(exc, json.JSONDecodeError):
            return f"bad response json: {exc}"
        return f"{type(exc).__name__}: {exc}"

    def _timed_infer(self, timeout_s: float, do_call: Callable[[float], dict[str, Any]]) -> tuple[dict[str, Any], float, str]:
        """执行推理调用并返回 (response_dict|None, latency_ms, error_str)。"""
        start = time.perf_counter()
        try:
            data = do_call(timeout_s)
            elapsed = (time.perf_counter() - start) * 1000.0
            return data, elapsed, ""
        except Exception as exc:  # noqa: BLE001 —— 节点层兜底契约：不外抛
            elapsed = (time.perf_counter() - start) * 1000.0
            return {}, elapsed, self._describe_error(exc)

    # ---- 公共结果组装 ----

    def _result(
        self,
        *,
        text: str = "",
        usage: dict[str, int] | None = None,
        latency_ms: float = 0.0,
        error: str = "",
    ) -> InferenceResult:
        p = self.profile
        return InferenceResult(
            ok=not error,
            text=text,
            node_id=p.node_id,
            tier=str(p.tier),
            model_id=p.model_id,
            latency_ms=round(latency_ms, 2),
            usage=usage or {},
            error=error,
        )
