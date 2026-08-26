# date: 2026-08-26
# dev: ox-alpha
"""端侧节点运行时：本机 Ollama 小模型适配器。

对应赛题答题要求 c"适配终端异构算力环境"——本地小模型即终端算力，
privacy=local 子任务的物理隔离保证（数据不出网卡）。

协议：Ollama REST ``POST /api/generate``（stream=false）、健康检查
``GET /api/tags``。失败一律返回 ``ok=False`` 的 :class:`InferenceResult`，
绝不向调度器抛网络异常。
"""

from __future__ import annotations

from infrastructure.nodes.base import BaseHttpNode
from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, Tier


class DeviceNode(BaseHttpNode):
    """端侧（device tier）节点：本机 Ollama 小模型。

    Attributes:
        profile: 节点档案（base_url 指向本机 Ollama，如 http://localhost:11434）。
    """

    def __init__(self, profile: NodeProfile) -> None:
        if str(profile.tier) != Tier.DEVICE:
            raise ValueError(f"DeviceNode requires tier=device, got {profile.tier}")
        super().__init__(profile)

    # ---- 健康检查 ----

    def health(self, timeout_s: float = 3.0) -> bool:
        """Ollama 可达即在线（GET /api/tags 2xx）。"""
        try:
            status, _ = self._get_json("/api/tags", timeout_s)
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
        """同步推理一次；timeout 缺省取档案 timeout_s，可按任务覆盖。"""
        payload = {
            "model": self.profile.model_id,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        data, elapsed, err = self._timed_infer(
            timeout_s if timeout_s is not None else self.profile.timeout_s,
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


__all__ = ["DeviceNode"]


if __name__ == "__main__":
    # 真机冒烟：python -m infrastructure.nodes.device.device_node
    _p = NodeProfile(
        node_id="device_local",
        tier=Tier.DEVICE,
        base_url="http://localhost:11434",
        provider="ollama",
        model_id="qwen2.5:0.5b",
    )
    _n = DeviceNode(_p)
    print(f"[health] {_n.health()}")
    _r = _n.infer("用一句话介绍你自己", max_tokens=64)
    print(f"[infer ] ok={_r.ok} latency={_r.latency_ms}ms usage={_r.usage}")
    print(f"[text ] {_r.text or _r.error}")
