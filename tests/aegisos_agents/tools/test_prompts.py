# date: 2026-08-03
# dev: 123 chen
"""Prompt 模块测试 — PromptRegistry + PromptRenderer。"""
import pytest

from aegisos_agents.tools.prompts.registry import PromptRegistry
from aegisos_agents.tools.prompts.renderer import PromptRenderer


@pytest.fixture
def registry():
    return PromptRegistry(seed=False)


@pytest.fixture
def seeded():
    return PromptRegistry(seed=True)


# ---- Registry 测试 ----

def test_register_new_template(registry):
    """注册新模板返回版本号 1。"""
    v = registry.register("test", "hello {{ name }}", role="red", variables=["name"])
    assert v == 1


def test_register_same_name_increments_version(registry):
    """同名再注册版本递增。"""
    registry.register("test", "v1", role="red")
    v2 = registry.register("test", "v2", role="red")
    assert v2 == 2


def test_get_latest_returns_highest_version(registry):
    """get 无版本参数返回最新版本。"""
    registry.register("test", "v1", role="red")
    registry.register("test", "v2", role="blue")
    tpl = registry.get("test")
    assert tpl is not None
    assert tpl.version == 2


def test_get_specific_version(registry):
    """按版本号精确查询。"""
    registry.register("test", "v1", role="red")
    _ = registry.register("test", "v2", role="blue")
    tpl = registry.get("test", version=1)
    assert tpl is not None
    assert tpl.version == 1
    assert tpl.role == "red"


def test_get_nonexistent_returns_none(registry):
    """查询不存在的模板返回 None。"""
    assert registry.get("nope") is None


def test_list_by_role(seeded):
    """按角色筛选模板。"""
    red = seeded.list_by_role("red")
    blue = seeded.list_by_role("blue")
    purple = seeded.list_by_role("purple")
    assert len(red) >= 4  # recon/vuln_correlator/exploit_planner/lateral_move
    assert len(blue) >= 4  # detector/triage/threat_hunt/ir_planner/forensics
    assert len(purple) >= 2  # critic_red/critic_blue/reviewer


def test_rollback_creates_new_version(registry):
    """回滚到过旧版本产生新版本。"""
    registry.register("test", "v1 content", role="red")
    registry.register("test", "v2 content", role="red")
    tpl = registry.rollback("test", 1)
    assert tpl is not None
    assert tpl.version == 3
    assert tpl.content == "v1 content"


def test_history_returns_all_versions(registry):
    """history 返回完整版本列表。"""
    registry.register("test", "v1")
    registry.register("test", "v2")
    registry.register("test", "v3")
    hist = registry.history("test")
    assert len(hist) == 3
    assert [h.version for h in hist] == [1, 2, 3]


# ---- Renderer 测试 ----

def test_render_simple_var_substitution():
    """render 将 {{ var }} 替换为实际值。"""
    result = PromptRenderer.render("Hello {{ name }}!", {"name": "World"})
    assert result == "Hello World!"


def test_render_multiple_vars():
    """render 支持多个变量替换。"""
    tpl = "Agent {{ agent }} scans {{ target }} for {{ vuln_type }} vulnerabilities."
    result = PromptRenderer.render(
        tpl,
        {"agent": "recon", "target": "192.168.1.0/24", "vuln_type": "CVE"},
    )
    assert "recon" in result
    assert "192.168.1.0/24" in result
    assert "CVE" in result


def test_render_missing_var_raises_value_error():
    """缺失变量时 render 抛 ValueError。"""
    with pytest.raises(ValueError, match="缺少变量"):
        PromptRenderer.render("Hello {{ name }}!", {})


def test_validate_returns_missing_vars():
    """validate 返回缺失变量列表。"""
    missing = PromptRenderer.validate("{{ a }} {{ b }} {{ c }}", {"a": "1"})
    assert set(missing) == {"b", "c"}


def test_validate_all_present_returns_empty():
    """变量全部提供时 validate 返回空列表。"""
    missing = PromptRenderer.validate("{{ x }}", {"x": "1"})
    assert missing == []


def test_extract_variables():
    """extract_variables 从模板中提取所有变量名。"""
    vars_ = PromptRenderer.extract_variables("{{ foo }} and {{ bar }} and {{ foo }}")
    assert vars_ == ["bar", "foo"]  # 去重排序
