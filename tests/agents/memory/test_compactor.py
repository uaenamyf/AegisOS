from agents.memory.compression.compactor import compress
from protocol.memory import MemoryPacket


def test_compress_keeps_decision_and_recent_makes_digest():
    ctx = [
        MemoryPacket(task_id="t1", kind="normal", recent=False, summary="noise"),
        MemoryPacket(task_id="t2", kind="decision", recent=False, summary="decide A"),
        MemoryPacket(task_id="t3", kind="normal", recent=True, summary="last step"),
    ]
    out = compress(ctx, budget=1)  # budget=1 triggers compression
    kinds = [m.kind for m in out]
    assert "decision" in kinds
    assert any(m.recent for m in out)
    assert "digest" in kinds
    digest = next(m for m in out if m.kind == "digest")
    assert digest.compression["count"] == 1
    assert "t1" in digest.compression["ids"]


def test_compress_noop_under_budget():
    ctx = [MemoryPacket(task_id="t1", summary="short")]
    assert compress(ctx, budget=1000) == ctx


def test_compress_all_decision_keeps_all():
    ctx = [
        MemoryPacket(task_id="t1", kind="decision", summary="decide A"),
        MemoryPacket(task_id="t2", kind="decision", summary="decide B"),
    ]
    out = compress(ctx, budget=1)
    assert len(out) == 2
    assert all(m.kind == "decision" for m in out)


def test_digest_summary_contains_folded_content():
    ctx = [
        MemoryPacket(task_id="t1", kind="normal", summary="alpha"),
        MemoryPacket(task_id="t2", kind="normal", summary="beta"),
    ]
    out = compress(ctx, budget=1)
    digest = next(m for m in out if m.kind == "digest")
    assert "alpha" in digest.summary
    assert "beta" in digest.summary
