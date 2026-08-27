"""R3 边侧节点运行时 —— 单元测试（mock HTTP 层，不依赖真实服务器）。

覆盖 EdgeNode 的两种 provider（ollama + aegis_edge）的所有路径：
正常推理、参数覆盖、异常兜底、健康检查、构造校验。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from infrastructure.nodes.descriptor import NodeProfile, ProviderKind, Tier
from infrastructure.nodes.edge.edge_node import EdgeNode

# ---- 测试常量 ----

OLLAMA_URL = "http://10.0.0.2:11434"
EDGE_URL = "http://10.0.0.2:8900"

OLLAMA_OK = {
    "response": "你好，我是边缘中型模型。",
    "prompt_eval_count": 50,
    "eval_count": 80,
    "total_duration": 2_000_000_000,
}

EDGE_OK = {
    "text": "你好，来自边缘服务。",
    "usage": {"prompt_tokens": 30, "completion_tokens": 60},
}


# ---- 辅助 ----

def _profile(**overrides) -> NodeProfile:
    base = dict(
        node_id="edge_server_01",
        tier=Tier.EDGE,
        base_url=EDGE_URL,
        provider=ProviderKind.AEGIS_EDGE,
        model_id="qwen2.5:7b",
        capabilities=["chat", "reasoning"],
        cost_weight=1.0,
        timeout_s=10.0,
    )
    base.update(overrides)
    return NodeProfile(**base)


class FakeResponse:
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


# ---- fixtures ----

@pytest.fixture()
def edge_node() -> EdgeNode:
    return EdgeNode(_profile())


@pytest.fixture()
def edge_ollama_node() -> EdgeNode:
    return EdgeNode(_profile(
        base_url=OLLAMA_URL,
        provider=ProviderKind.OLLAMA,
    ))


# ============ aegis_edge provider ============


def test_infer_aegis_edge_happy_path(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    """POST /infer 正常路径：边缘服务返回 ok。"""
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(json.dumps(EDGE_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = edge_node.infer("一句话介绍你自己", system="你是边缘攻防助手")

    assert result.ok is True
    assert result.text == EDGE_OK["text"]
    assert result.node_id == "edge_server_01"
    assert result.tier == "edge"
    assert result.model_id == "qwen2.5:7b"
    assert result.usage["prompt_tokens"] == 30
    assert result.usage["completion_tokens"] == 60
    assert result.latency_ms >= 0
    assert result.error == ""
    assert captured["url"] == f"{EDGE_URL}/infer"
    assert captured["body"]["prompt"] == "一句话介绍你自己"
    assert captured["body"]["system"] == "你是边缘攻防助手"


def test_infer_aegis_edge_overrides(
    edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch
):
    """aegis_edge 参数覆盖：temperature、max_tokens 透传。"""
    body_holder = {}

    def fake_urlopen(req, timeout=None):
        body_holder["b"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(json.dumps(EDGE_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    edge_node.infer("hi", temperature=0.3, max_tokens=256)
    assert body_holder["b"]["max_tokens"] == 256
    assert body_holder["b"]["temperature"] == pytest.approx(0.3)


def test_infer_aegis_edge_timeout_propagates(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    """自定义 timeout 覆盖 profile 默认值。"""
    timeout_holder = {}

    def fake_urlopen(req, timeout=None):
        timeout_holder["t"] = timeout
        return FakeResponse(json.dumps(EDGE_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    edge_node.infer("hi", timeout_s=3.0)
    assert timeout_holder["t"] == pytest.approx(3.0)


# ============ ollama provider ============


def test_infer_ollama_happy_path(
    edge_ollama_node: EdgeNode, monkeypatch: pytest.MonkeyPatch
):
    """Ollama provider：复用 POST /api/generate 协议。"""
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(json.dumps(OLLAMA_OK).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = edge_ollama_node.infer("hi")

    assert result.ok is True
    assert result.text == OLLAMA_OK["response"]
    assert captured["url"] == f"{OLLAMA_URL}/api/generate"
    assert captured["body"]["stream"] is False


# ============ 失败路径（绝不抛异常） ============


def test_connection_refused_returns_error(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = edge_node.infer("hi")
    assert result.ok is False
    assert result.text == ""
    assert "refused" in result.error.lower()


def test_timeout_returns_error(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = edge_node.infer("hi")
    assert result.ok is False
    assert "timed out" in result.error.lower()


def test_http_500_returns_error(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = edge_node.infer("hi")
    assert result.ok is False
    assert "500" in result.error


# ============ 健康检查 ============


def test_health_aegis_edge_true(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse(b'{"status":"ok","cache_size":3}'),
    )
    assert edge_node.health() is True


def test_health_ollama_true(edge_ollama_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse(b'{"models": []}'),
    )
    assert edge_ollama_node.health() is True


def test_health_false_on_refused(edge_node: EdgeNode, monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("nope")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert edge_node.health() is False


# ============ 构造校验 ============


def test_rejects_non_edge_profile():
    with pytest.raises(ValueError):
        EdgeNode(NodeProfile(node_id="d", tier=Tier.DEVICE))

    with pytest.raises(ValueError):
        EdgeNode(NodeProfile(node_id="c", tier=Tier.CLOUD))


def test_from_profile_factory():
    n = EdgeNode.from_profile(_profile())
    assert n.profile.node_id == "edge_server_01"