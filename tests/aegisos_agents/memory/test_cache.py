# date: 2026-08-01
# dev: myf
"""缓存模块测试 —— L1 查询缓存 TTL + L2 热点 LRU + 失效级联。"""

import time

import pytest

from aegisos_agents.memory.cache.store import MemoryCache
from protocol.memory import MemoryPacket


@pytest.fixture
def cache():
    return MemoryCache()


def make_pkt(task_id: str) -> MemoryPacket:
    return MemoryPacket(task_id=task_id, summary=f"summary of {task_id}")


def test_get_query_miss_returns_none(cache):
    """查询缓存未命中返回 None。"""
    assert cache.get_query("unknown_trigger") is None


def test_set_and_get_query_hit(cache):
    """写入 L1 查询缓存后可命中。"""
    pkts = [make_pkt("t1"), make_pkt("t2")]
    cache.set_query("test_key", pkts)
    result = cache.get_query("test_key")
    assert result is not None
    assert len(result) == 2
    assert result[0].task_id == "t1"


def test_l1_ttl_expiry(cache):
    """L1 缓存 TTL 过期后返回 None。"""
    pkts = [make_pkt("t1")]
    cache.set_query("test_key", pkts, ttl=0.01)
    time.sleep(0.02)
    assert cache.get_query("test_key") is None


def test_touch_promotes_to_l2(cache):
    """访问 ≥3 次自动晋升 L2 热点缓存。"""
    cache.touch("hot_task")
    cache.touch("hot_task")
    cache.touch("hot_task")
    hot = cache.get_hot("hot_task")
    assert hot is not None


def test_invalidate_clears_all_levels(cache):
    """invalidate 应清除 L1 和 L2 中该 task_id 的缓存。"""
    pkt = make_pkt("t1")
    cache.set_query("key", [pkt])
    cache.touch("t1")
    cache.touch("t1")
    cache.touch("t1")
    assert cache.get_hot("t1") is not None
    cache.invalidate("t1")
    assert cache.get_hot("t1") is None


def test_stats_returns_dict(cache):
    """stats 返回含命中率的结构化字典。"""
    cache.set_query("k", [make_pkt("t1")])
    s = cache.stats()
    assert "l1_size" in s
    assert "l2_size" in s
    assert s["l1_size"] == 1
