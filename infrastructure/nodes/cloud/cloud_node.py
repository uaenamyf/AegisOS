# date: 2026-08-27
# dev: ox-alpha
"""云侧节点运行时：OpenAI 兼容 ChatCompletions API 适配器。

对应赛题答题要求 C-5"充分利用云端算力处理高复杂度子任务"——
CloudNode 是云侧算力的实际执行者，接收 R6 派发器按"算力优先"规则
路由过来的任务，返回 InferenceResult。

协议：OpenAI 兼容 ChatCompletions API（``POST /v1/chat/completions``）。
认证：Authorization Bearer Token 来自 ``OPENAI_API_KEY`` 环境变量。
"""

from __future__ import annotations

import os

from infrastructure.nodes.base import BaseHttpNode
from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, Tier


class CloudNode(BaseHttpNode):
    """云侧（cloud tier）节点：OpenAI 兼容 ChatCompletions API。

    Attributes:
        profile: 节点档案（base_url 指向 API 根，如 https://api.openai.com/v1）。
        _api_key: 从 OPENAI_API_KEY 环境变量读取的 API Key；空字符串表示未配置。
    """

    def __init__(self, profile: NodeProfile) -> None:
        if str(profile.tier) != Tier.CLOUD:
            raise ValueError(f"CloudNode requires tier=cloud, got {profile.tier}")
        super().__init__(profile)
        self._api_key: str = os.getenv("OPENAI_API_KEY", "")

    # ---- 健康检查 ----

    def health(self, timeout_s: float = 5.0) -> bool:
        """API Key 已配置且 API 端点可达即为在线。

        检查策略：先检查环境变量，再尝试轻量 GET /models。
        """
        if not self._api_key:
            return False
        try:
            status, _ = self._get_json(
                "/models",
                timeout_s,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
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
        """同步推理一次；timeout 缺省取档案 timeout_s，可按任务覆盖。

        Args:
            prompt: 用户输入文本。
            system: 可选系统提示词（作为 system message 前置）。
            temperature: 生成温度（0.0-2.0）。
            max_tokens: 最大输出 token 数。
            timeout_s: 超时秒数；None 时使用 profile.timeout_s。

        Returns:
            InferenceResult：ok=True 时 text 含 API 回复；
            ok=False 时 error 含失败原因，绝不抛异常。
        """
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.profile.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        # DeepSeek V4 系列为思考模型：默认会把 token 花在 reasoning_content 上
        # 导致 content 为空。对 deepseek 端点显式关闭思考，保证直接产出答案。
        if "deepseek" in (self.profile.base_url or "").lower() or "deepseek" in (
            self.profile.model_id or ""
        ).lower():
            payload["thinking"] = {"type": "disabled"}

        auth_headers = {"Authorization": f"Bearer {self._api_key}"}

        data, elapsed, err = self._timed_infer(
            timeout_s if timeout_s is not None else self.profile.timeout_s,
            lambda t: self._post_json(
                "/chat/completions", payload, t, headers=auth_headers
            ),
        )
        if err:
            return self._result(latency_ms=elapsed, error=err)

        # 解析 OpenAI ChatCompletions 响应
        text = ""
        usage: dict = {}
        try:
            text = data["choices"][0]["message"]["content"]
            usage = {
                "prompt_tokens": int(data.get("usage", {}).get("prompt_tokens", 0) or 0),
                "completion_tokens": int(
                    data.get("usage", {}).get("completion_tokens", 0) or 0
                ),
            }
        except (KeyError, IndexError, TypeError):
            text = str(data)

        return self._result(text=text, usage=usage, latency_ms=elapsed)


__all__ = ["CloudNode"]


if __name__ == "__main__":
    # 真机冒烟：python -m infrastructure.nodes.cloud.cloud_node
    import os

    _p = NodeProfile(
        node_id="cloud_api",
        tier=Tier.CLOUD,
        base_url="https://api.openai.com/v1",
        provider="openai_api",
        model_id="gpt-4o",
    )
    _n = CloudNode(_p)
    print(f"[health] {_n.health()}")
    if _n._api_key:
        _r = _n.infer("用一句话介绍你自己", max_tokens=64)
        print(f"[infer ] ok={_r.ok} latency={_r.latency_ms}ms usage={_r.usage}")
        print(f"[text ] {_r.text or _r.error}")
    else:
        print("[skip ] 无 OPENAI_API_KEY，跳过推理冒烟")