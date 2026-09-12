"""R2 端侧节点运行时 —— 单元测试（mock HTTP 层，不依赖真实 Ollama）。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from infrastructure.nodes.descriptor import NodeProfile, ProviderKind, Tier
from infrastructure.nodes.device.device_node import DeviceNode

REPO = "http://localhost:11434"

OLLAMA_OK = {
    "response": "你好，我是本地小模型。",
    "prompt_eval_count": 12,
    "eval_count": 20,
    "total_duration": 800_000_000,
}


def _profile(**overrides) -> NodeProfile:
    base = dict(
        node_id="device_local",
        tier=Tier.DEVICE,
        base_url=REPO,
        provider=ProviderKind.OLLAMA,
        model_id="qwen2.5:0.5b",
        capabilities=["chat"],
        cost_weight=0.1,
        timeout_s=5.0,
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
def node() -> DeviceNode:
    return DeviceNode(_profile())


# ---------- 正常路径 ----------


def test_infer_happy_path(node: DeviceNode, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(json.dumps(OLLAMA_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("一句话介绍你自己", system="你是攻防助手")

    assert result.ok is True
    assert result.text == OLLAMA_OK["response"]
    assert result.node_id == "device_local"
    assert result.tier == "device"
    assert result.model_id == "qwen2.5:0.5b"
    assert result.usage["prompt_tokens"] == 12
    assert result.usage["completion_tokens"] == 20
    assert result.latency_ms >= 0
    assert result.error == ""
    # 请求体正确组装
    assert captured["url"] == f"{REPO}/api/generate"
    assert captured["body"]["model"] == "qwen2.5:0.5b"
    assert captured["body"]["system"] == "你是攻防助手"
    assert captured["body"]["stream"] is False
    assert captured["body"]["options"]["num_predict"] == 512
    assert captured["timeout"] == pytest.approx(5.0)


def test_infer_overrides(node: DeviceNode, monkeypatch: pytest.MonkeyPatch):
    body_holder = {}

    def fake_urlopen(req, timeout=None):
        body_holder["b"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(json.dumps(OLLAMA_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    node.infer("hi", temperature=0.1, max_tokens=64)
    assert body_holder["b"]["options"]["temperature"] == pytest.approx(0.1)
    assert body_holder["b"]["options"]["num_predict"] == 64


# ---------- 失败路径（绝不抛异常） ----------


def test_connection_refused_returns_error_result(
    node: DeviceNode, monkeypatch: pytest.MonkeyPatch
):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("hi")
    assert result.ok is False
    assert result.text == ""
    assert "refused" in result.error.lower()


def test_timeout_returns_error_result(node: DeviceNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("hi")
    assert result.ok is False
    assert "timed out" in result.error.lower()


def test_http_500_returns_error_result_with_status(
    node: DeviceNode, monkeypatch: pytest.MonkeyPatch
):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = node.infer("hi")
    assert result.ok is False
    assert "500" in result.error


def test_malformed_json_returns_error_result(
    node: DeviceNode, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=None: FakeResponse(b"not-json{")
    )
    result = node.infer("hi")
    assert result.ok is False


# ---------- 健康检查 ----------


def test_health_true_on_200(node: DeviceNode, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse(b'{"models": []}'),
    )
    assert node.health() is True


def test_health_false_on_refused(node: DeviceNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("nope")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert node.health() is False


# ---------- 构造 ----------


def test_rejects_non_device_profile():
    with pytest.raises(ValueError):
        DeviceNode(NodeProfile(node_id="c", tier=Tier.CLOUD))


def test_from_profile_factory():
    n = DeviceNode.from_profile(_profile())
    assert n.profile.node_id == "device_local"
