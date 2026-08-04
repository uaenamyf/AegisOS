# date: 2026-08-01
# dev: 123 chen
"""反思模块测试 —— ExecutionCritic + OutputScorer + FeedbackLoop。"""
import pytest
from aegisos_agents.perception.reflection.critic import Critique, ExecutionCritic
from aegisos_agents.perception.reflection.scoring import OutputScore, OutputScorer
from aegisos_agents.perception.reflection.feedback import FeedbackLoop, FeedbackRecord


# ---- ExecutionCritic 测试 ----

@pytest.fixture
def critic():
    return ExecutionCritic()


def test_critique_missing_required_field(critic):
    """检测缺失必需字段 → high 严重度。"""
    output = {"name": "test"}  # 缺少 expected 字段 "assets"
    critiques = critic.critique(output, expected_fields=["name", "assets"])
    assert any(c.severity == "high" and c.field == "assets" for c in critiques)


def test_critique_empty_output(critic):
    """空输出 → high 严重度。"""
    critiques = critic.critique({})
    assert any(c.dimension == "emptiness" and c.severity == "high" for c in critiques)


def test_critique_empty_key_field(critic):
    """关键字段为空列表 → medium 严重度。"""
    output = {"assets": []}
    critiques = critic.critique(output, expected_fields=["assets"])
    assert any(c.dimension == "emptiness" for c in critiques)


def test_critique_destructive_action(critic):
    """检测破坏性操作标记 → high 严重度。"""
    output = {"action": "rm -rf /tmp/data", "target": "host_A"}
    critiques = critic.critique(output)
    assert any(
        "破坏性操作" in c.message and c.severity == "high" for c in critiques
    )


def test_critique_perfect_output(critic):
    """完整且完美的输出应无批判。"""
    output = {"name": "recon", "assets": [{"host": "192.168.1.1", "ports": [80, 443]}]}
    critiques = critic.critique(output, expected_fields=["assets"])
    assert len(critiques) == 0


def test_has_blocker(critic):
    """has_blocker 正确识别高严重度问题。"""
    critiques = [
        Critique(dimension="emptiness", severity="high", message="输出为空"),
        Critique(dimension="sanity", severity="low", message="端口号偏大"),
    ]
    assert critic.has_blocker(critiques) is True
    assert critic.has_blocker(critiques[1:]) is False


# ---- OutputScorer 测试 ----

@pytest.fixture
def scorer():
    return OutputScorer()


def test_score_perfect_output(scorer):
    """完美输出应得满分 success。"""
    output = {"assets": [{"host": "192.168.1.1"}], "name": "recon"}
    result = scorer.score(output, critiques=[], expected_fields=["assets", "name"])
    assert result.overall >= 0.8
    assert result.grade == "success"


def test_score_with_critiques(scorer):
    """有批判时分数应降低。"""
    critiques = [
        Critique(dimension="emptiness", severity="high", message="assets 为空"),
    ]
    output = {"assets": []}
    result = scorer.score(output, critiques, expected_fields=["assets"])
    assert result.overall < 0.8
    assert result.grade in ("pass", "fail")


def test_score_fails_grade(scorer):
    """大量严重批判 → fail。"""
    critiques = [Critique(dimension="emptiness", severity="high", message=str(i)) for i in range(6)]
    result = scorer.score({}, critiques, expected_fields=["assets"])
    assert result.grade == "fail"
    assert result.correctness < 0.5


def test_quick_score(scorer):
    """quick_score 不依赖批判列表。"""
    output = {"assets": [{"host": "a"}], "name": "recon"}
    result = scorer.quick_score(output, expected_fields=["assets", "name", "missing"])
    assert 0.0 <= result.overall <= 1.0
    assert result.grade in ("success", "pass", "fail")


def test_efficiency_scoring(scorer):
    """步骤数影响效率分。"""
    # 1 步 → 满分效率
    result_1 = scorer.score({"a": 1}, [], step_count=1)
    # 11 步 → 效率分减半
    result_11 = scorer.score({"a": 1}, [], step_count=11)
    assert result_1.efficiency > result_11.efficiency


# ---- FeedbackLoop 测试 ----

@pytest.fixture
def loop():
    return FeedbackLoop()


def test_reflect_produces_record(loop):
    """reflect 产生完整的 FeedbackRecord。"""
    output = {"assets": [{"host": "192.168.1.1", "ports": [80]}], "name": "recon"}
    record = loop.reflect(
        agent_id="recon",
        task_id="t1",
        output=output,
        expected_fields=["assets", "name"],
    )
    assert isinstance(record, FeedbackRecord)
    assert record.agent_id == "recon"
    assert record.task_id == "t1"
    assert record.grade in ("success", "pass", "fail")
    assert record.summary != ""


def test_reflect_without_engine(loop):
    """无 reflection_engine 时也应正常完成（降级）。"""
    output = {"assets": [], "name": "recon"}
    record = loop.reflect(
        agent_id="recon", task_id="t1", output=output, expected_fields=["assets"]
    )
    assert record.grade in ("fail", "pass")  # 空 assets 会降低评分


def test_batch_reflect(loop):
    """批量反思返回多个 FeedbackRecord。"""
    results = [
        {"agent_id": "recon", "task_id": "t1", "output": {"assets": [{"host": "a"}]}},
        {"agent_id": "detector", "task_id": "t2", "output": {"alerts": [{"id": 1}]}},
    ]
    records = loop.batch_reflect(results)
    assert len(records) == 2
    assert records[0].agent_id == "recon"
    assert records[1].agent_id == "detector"


def test_reflect_score_writes_to_reflection_engine(loop):
    """reflect 写回 memory/reflection 验证：tag_outcome + record_reference。"""
    from aegisos_agents.memory.reflection.engine import ReflectionEngine
    engine = ReflectionEngine()
    output = {"assets": [{"host": "192.168.1.1"}], "name": "recon"}
    loop.reflect(
        agent_id="recon",
        task_id="write_test_t1",
        output=output,
        expected_fields=["assets", "name"],
        reflection_engine=engine,
    )
    # 确认 ReflectionEngine 记录了结果
    assert engine.get_reference_count("write_test_t1") >= 1
