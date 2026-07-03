from protocol.memory import MemoryPacket
from agents.memory.recall.recaller import recall


def test_recall_returns_decision_packets_matching_trigger():
    episodic = [
        MemoryPacket(task_id="e1", kind="decision", summary="decide to isolate h1"),
        MemoryPacket(task_id="e2", kind="normal", summary="scanned h2"),
    ]
    vector = [
        MemoryPacket(task_id="v1", kind="decision", summary="isolate host"),
    ]
    result = recall("isolate", episodic, vector)
    ids = [m.task_id for m in result]
    assert "e1" in ids   # episodic decision matching trigger
    assert "v1" in ids  # vector top_k matching trigger


def test_recall_prioritizes_decision_kind():
    episodic = [
        MemoryPacket(task_id="e1", kind="decision", summary="isolate h1"),
        MemoryPacket(task_id="e2", kind="normal", summary="isolate h2"),
    ]
    result = recall("isolate", episodic, [])
    decision_results = [m for m in result if m.kind == "decision"]
    normal_results = [m for m in result if m.kind == "normal"]
    assert len(decision_results) >= 1
    # decisions come first
    assert result[0].kind == "decision"


def test_recall_empty_when_no_match():
    episodic = [MemoryPacket(task_id="e1", summary="nothing relevant")]
    result = recall("nonexistent", episodic, [])
    assert result == []
