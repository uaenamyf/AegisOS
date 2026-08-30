# date: 2026-08-27
# dev: ox-alpha
"""边侧节点运行时：服务器 Ollama 中型模型 / 自有边缘服务适配器。

对应赛题答题要求 c"适配边缘异构算力环境"——边缘服务器即赛题中的边缘算力，
privacy=standard 子任务的区域隔离保证。

支持两种 provider：
    - ollama：服务器跑 Ollama，协议与 DeviceNode 同为 POST /api/generate
    - aegis_edge：服务器跑我们自带的极简边缘服务（edge_server.py），
      协议为 POST /infer + GET /health

异常一律返回 ok=False 的 InferenceResult，绝不向调度器抛网络异常。
"""

from __future__ import annotations

from infrastructure.nodes.base import BaseHttpNode
from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, ProviderKind, Tier


class EdgeNode(BaseHttpNode):
    """边侧（edge tier）节点：服务器中型模型。

    Attributes:
        profile: 节点档案（base_url 指向边缘服务器，如 http://10.0.0.2:8900）。
    """

    def __init__(self, profile: NodeProfile) -> None:
        if str(profile.tier) != Tier.EDGE:
            raise ValueError(f"EdgeNode requires tier=edge, got {profile.tier}")
        super().__init__(profile)

    # ---- 健康检查 ----

    def health(self, timeout_s: float = 3.0) -> bool:
        """探测边缘节点是否在线。

        aegis_edge 走 GET /health（2xx 即在线），
        ollama 走 GET /api/tags（与 DeviceNode 一致）。
        """
        try:
            path = "/health" if self.profile.provider == "aegis_edge" else "/api/tags"
            status, _ = self._get_json(path, timeout_s)
            return 200 <= status < 300
        except Exception:  # noqa: BLE001 —— 探活失败即离线
            return False

    # ---- 推理 ----

    def infer(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout_s: float | None = None,
    ) -> InferenceResult:
        """同步推理一次；provider 分支选择协议。

        timeout_s 缺省取档案值，可按任务覆盖。
        """
        effective_timeout = (
            timeout_s if timeout_s is not None else self.profile.timeout_s
        )

        if self.profile.provider == "ollama":
            return self._infer_ollama(
                prompt, system, temperature, max_tokens, effective_timeout
            )
        # aegis_edge（默认）
        return self._infer_aegis_edge(
            prompt, system, temperature, max_tokens, effective_timeout
        )

    # ---- 私有：aegis_edge 协议 ----

    def _infer_aegis_edge(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
    ) -> InferenceResult:
        payload = {
            "prompt": prompt,
            "system": system,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data, elapsed, err = self._timed_infer(
            timeout_s,
            lambda t: self._post_json("/infer", payload, t),
        )
        if err:
            return self._result(latency_ms=elapsed, error=err)
        return self._result(
            text=str(data.get("text", "")),
            usage={
                "prompt_tokens": int(data.get("usage", {}).get("prompt_tokens", 0) or 0),
                "completion_tokens": int(
                    data.get("usage", {}).get("completion_tokens", 0) or 0
                ),
            },
            latency_ms=elapsed,
        )

    # ---- 私有：ollama 协议 ----

    def _infer_ollama(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
    ) -> InferenceResult:
        payload = {
            "model": self.profile.model_id,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        data, elapsed, err = self._timed_infer(
            timeout_s,
            lambda t: self._post_json("/api/generate", payload, t),
        )
        if err:
            return self._result(latency_ms=elapsed, error=err)
        return self._result(
            text=str(data.get("response", "")),
            usage={
                "prompt_tokens": int(data.get("prompt_eval_count", 0) or 0),
                "completion_tokens": int(data.get("eval_count", 0) or 0),
            },
            latency_ms=elapsed,
        )


__all__ = ["EdgeNode"]


if __name__ == "__main__":
    # 真机冒烟（需 edge_server 运行在 localhost:8900）：
    #   python tooling/scripts/edge_server.py  # 终端 1
    #   python -m infrastructure.nodes.edge.edge_node  # 终端 2
    _p = NodeProfile(
        node_id="edge_server_01",
        tier=Tier.EDGE,
        base_url="http://localhost:8900",
        provider=ProviderKind.AEGIS_EDGE,
        model_id="qwen2.5:7b",
        capabilities=["chat", "reasoning"],
        timeout_s=10.0,
    )
    _n = EdgeNode(_p)
    print(f"[health] {_n.health()}")
    _r = _n.infer("用一句话介绍你自己", max_tokens=64)
    print(f"[infer ] ok={_r.ok} latency={_r.latency_ms}ms usage={_r.usage}")
    print(f"[text ] {_r.text or _r.error}")
