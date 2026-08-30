"""R6 执行派发器集成测试 —— 调度决策→真实执行降级链路验证。

覆盖计划场景：
    ① 正常选云
    ② device 失联降级 edge
    ③ edge 也失联直达 cloud
    ④ 全部失联返回失败
    ⑤ privacy=local 强制端侧且端侧在线
"""

from __future__ import annotations

from infrastructure.nodes.descriptor import NodeProfile, Tier
from infrastructure.nodes.dispatcher import ExecutionDispatcher
from infrastructure.nodes.registry import NodeRegistry
from protocol.scheduler import Task


class _FakeNode:
    """可控健康状态与推理结果的假节点（不依赖真实 HTTP）。"""

    def __init__(self, profile: NodeProfile, *, health_ok: bool = True, infer_ok: bool = True):
        self.profile = profile
        self._health_ok = health_ok
        self._infer_ok = infer_ok
        self.infer_calls = 0

    def health(self, timeout_s: float = 3.0) -> bool:
        return self._health_ok

    def set_health(self, ok: bool) -> None:
        self._health_ok = ok

    def set_infer_ok(self, ok: bool) -> None:
        self._infer_ok = ok

    def infer(self, prompt: str, *, system: str = "", **kwargs):
        from infrastructure.nodes.descriptor import InferenceResult
        self.infer_calls += 1
        if not self._infer_ok:
            return InferenceResult.failure(
                error="fake infer failure", node_id=self.profile.node_id, tier=str(self.profile.tier)
            )
        return InferenceResult(
            ok=True,
            text=f"[{self.profile.node_id}] {prompt}",
            node_id=self.profile.node_id,
            tier=str(self.profile.tier),
            model_id=self.profile.model_id,
            latency_ms=10.0,
            usage={"prompt_tokens": 5, "completion_tokens": 3},
        )


def _profiles():
    return {
        "device": NodeProfile(node_id="device_local", tier=Tier.DEVICE,
                               model_id="tiny", capabilities=["chat"]),
        "edge": NodeProfile(node_id="edge_01", tier=Tier.EDGE,
                            model_id="medium", capabilities=["chat", "reasoning"]),
        "cloud": NodeProfile(node_id="cloud_api", tier=Tier.CLOUD,
                             provider="openai_api", model_id="large",
                             capabilities=["chat", "reasoning", "long_context"]),
    }


def _make_registry(fake_nodes: dict[str, _FakeNode]) -> NodeRegistry:
    reg = NodeRegistry()
    for node in fake_nodes.values():
        reg.register_node(node)
    # 全部标记 online（探活一次）
    reg.tick()
    return reg


def _task(**overrides) -> Task:
    base = dict(goal="test", latency_budget=10.0, privacy="standard")
    base.update(overrides)
    return Task(**base)


# ---------- ① 正常选云 ----------

def test_normal_dispatch_routes_to_cloud():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    reg = _make_registry(fake)
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(goal="复杂推理", latency_budget=10.0), "hi")
    assert result.ok is True
    assert result.tier == "cloud"
    assert result.node_id == "cloud_api"


# ---------- ⑤ privacy=local 强制端侧 ----------

def test_privacy_local_forces_device():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    reg = _make_registry(fake)
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(privacy="local"), "secret")
    assert result.ok is True
    assert result.tier == "device"


# ---------- ② device 失联降级 edge ----------

def test_device_unhealthy_degrades_to_edge():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    # device 离线 → 注册表 discover 不含 device
    fake["device"].set_health(False)
    reg = _make_registry(fake)
    # 连续心跳让 device 变 offline
    reg.tick()
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(privacy="local"), "secret")
    # device 离线，local 任务降级到 edge
    assert result.tier == "edge"


# ---------- ③ edge 也失联直达 cloud ----------

def test_edge_unhealthy_goes_cloud():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    fake["device"].set_health(False)
    fake["edge"].set_health(False)
    reg = _make_registry(fake)
    reg.tick()  # 让 device/edge 均标记 offline
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(privacy="local"), "secret")
    assert result.tier == "cloud"


# ---------- ④ 全部失联返回失败 ----------

def test_all_unhealthy_returns_failure():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    for node in fake.values():
        node.set_health(False)
    reg = _make_registry(fake)
    reg.tick()
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(), "hi")
    assert result.ok is False
    assert "error" in result.error.lower() or result.error != ""


# ---------- 附加：执行失败触发降级（非健康问题） ----------

def test_infer_failure_triggers_degradation():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    # cloud 推理失败 → 降级到 edge
    fake["cloud"].set_infer_ok(False)
    reg = _make_registry(fake)
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(goal="重活", latency_budget=10.0), "hi")
    assert result.tier == "edge"
    assert result.ok is True


# ---------- 附加：attempts 轨迹记录 ----------

def test_attempts_recorded():
    fake = {k: _FakeNode(p) for k, p in _profiles().items()}
    fake["cloud"].set_infer_ok(False)
    reg = _make_registry(fake)
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(goal="重活", latency_budget=10.0), "hi")
    assert result.attempts  # 非空
    # 云尝试失败 + 边成功
    tiers = [a["tier"] for a in result.attempts]
    assert "cloud" in tiers
    assert "edge" in tiers


# ---------- 附加：无节点返回失败 ----------

def test_no_nodes_returns_failure():
    reg = NodeRegistry()
    disp = ExecutionDispatcher(reg)
    result = disp.dispatch(_task(), "hi")
    assert result.ok is False


def test_max_attempts_bounded():
    fake = {k: _FakeNode(p, infer_ok=False) for k, p in _profiles().items()}
    reg = _make_registry(fake)
    disp = ExecutionDispatcher(reg, max_attempts=3)
    result = disp.dispatch(_task(goal="重活", latency_budget=10.0), "hi")
    assert result.ok is False
    # attempts 不超过 3
    assert len(result.attempts) <= 3
