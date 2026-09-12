"""R4 云侧节点运行时 —— 单元测试（mock HTTP 层，不依赖真实 API）。

验证 CloudNode 的 OpenAI 兼容 ChatCompletions 调用：健康检查、推理、
超时/认证失败/API 错误等异常翻译、tier 守卫、工厂构造。
"""

from __future__ import annotations

import json
import urllib.request

import pytest

from infrastructure.nodes.cloud.cloud_node import CloudNode
from infrastructure.nodes.descriptor import NodeProfile, ProviderKind, Tier

REPO = "https://api.openai.com/v1"

CHAT_OK = {
    "choices": [{"message": {"content": "你好，我是云侧大模型。"}, "index": 0}],
    "usage": {"prompt_tokens": 15, "completion_tokens": 25},
    "model": "gpt-4o",
}


def _profile(**overrides) -> NodeProfile:
    base = dict(
        node_id="cloud_api",
        tier=Tier.CLOUD,
        base_url=REPO,
        provider=ProviderKind.OPENAI_API,
        model_id="gpt-4o",
        capabilities=["chat", "reasoning", "long_context"],
        cost_weight=10.0,
        timeout_s=30.0,
    )
    base.update(overrides)
    return NodeProfile(**base)


class FakeResponse:
    """伪造 urlopen 返回对象（支持 with 上下文）。"""

    def __init__(self, payload: bytes, status: int = 200):
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


@pytest.fixture()
def node(monkeypatch: pytest.MonkeyPatch) -> CloudNode:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    return CloudNode(_profile())


# ---------- 正常路径 ----------


def test_infer_happy_path(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        captured["headers"] = {k: v for k, v in req.headers.items()}
        return FakeResponse(json.dumps(CHAT_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("介绍一下你自己")

    assert result.ok is True
    assert "云侧大模型" in result.text
    assert result.usage["prompt_tokens"] == 15
    assert result.usage["completion_tokens"] == 25
    assert result.tier == "cloud"
    assert result.latency_ms > 0
    # 验证请求体符合 OpenAI ChatCompletions 格式
    assert captured["body"]["model"] == "gpt-4o"
    assert captured["body"]["messages"][0]["role"] == "user"
    assert captured["body"]["messages"][0]["content"] == "介绍一下你自己"
    # 验证 API Key 已注入 Authorization 头
    assert "Authorization" in captured["headers"]
    assert captured["headers"]["Authorization"] == "Bearer sk-test-key"


def test_infer_with_system_prompt(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(json.dumps(CHAT_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    node.infer("分析日志", system="你是一个安全分析专家")
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][0]["content"] == "你是一个安全分析专家"


def test_infer_overrides_defaults(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(json.dumps(CHAT_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    node.infer("test", temperature=0.1, max_tokens=2048, timeout_s=60.0)
    assert captured["body"]["temperature"] == 0.1
    assert captured["body"]["max_tokens"] == 2048
    assert captured["timeout"] == 60.0


# ---------- 健康检查 ----------


def test_health_returns_true_when_key_set_and_api_reachable(
    node: CloudNode, monkeypatch: pytest.MonkeyPatch
):
    def fake_urlopen(req, timeout=None):
        return FakeResponse(json.dumps({"data": [{"id": "gpt-4o"}]}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert node.health() is True


def test_health_returns_false_when_no_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    n = CloudNode(_profile())
    assert n.health() is False


def test_health_returns_false_on_connection_error(
    node: CloudNode, monkeypatch: pytest.MonkeyPatch
):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert node.health() is False


# ---------- 异常翻译 ----------


def test_connection_refused_returns_error(
    node: CloudNode, monkeypatch: pytest.MonkeyPatch
):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("[Errno 111] Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("test")
    assert result.ok is False
    assert "connection" in result.error.lower() or "Connection" in result.error


def test_timeout_returns_error(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("test")
    assert result.ok is False


def test_http_401_returns_error(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            url=req.full_url, code=401, msg="Unauthorized", hdrs={}, fp=None
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("test")
    assert result.ok is False
    assert "401" in result.error


# ---------- 构造与守卫 ----------


def test_from_profile_factory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    n = CloudNode.from_profile(_profile())
    assert isinstance(n, CloudNode)
    assert n.profile.node_id == "cloud_api"


def test_tier_guard_rejects_non_cloud():
    p = _profile(tier=Tier.DEVICE)
    with pytest.raises(ValueError, match="tier=cloud"):
        CloudNode(p)


def test_latency_measured(node: CloudNode, monkeypatch: pytest.MonkeyPatch):

    def fake_urlopen(req, timeout=None):
        return FakeResponse(json.dumps(CHAT_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("test")
    assert result.latency_ms > 0


def test_anthropic_messages_provider(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    captured = {}
    profile = _profile(
        provider=ProviderKind.ANTHROPIC,
        api_path="/messages",
        health_path="/models",
    )
    anthropic_node = CloudNode(profile)

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        return FakeResponse(json.dumps({"content": [{"type": "text", "text": "Anthropic OK"}]}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = anthropic_node.infer("分析告警")

    assert result.ok is True
    assert result.text == "Anthropic OK"
    assert captured["url"].endswith("/messages")
    assert captured["body"]["messages"][0]["content"] == "分析告警"
    assert captured["headers"]["x-api-key"] == "sk-test-key"


def test_custom_json_provider(node: CloudNode, monkeypatch: pytest.MonkeyPatch):
    captured = {}
    profile = _profile(
        provider=ProviderKind.CUSTOM,
        request_format="json",
        api_path="/generate",
        api_key_header="X-Token",
    )
    custom_node = CloudNode(profile)

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        return FakeResponse(json.dumps({"output": "Custom OK"}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = custom_node.infer("检查资产")

    assert result.ok is True
    assert result.text == "Custom OK"
    assert captured["url"].endswith("/generate")
    assert captured["body"]["model"] == "gpt-4o"
    assert captured["headers"]["x-token"] == "sk-test-key"
