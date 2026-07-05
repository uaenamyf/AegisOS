from aegisos_agents.planning.engine.router.election import elect
from protocol.graph import GraphNode, NodeKind


def test_elect_picks_best_capability_match():
    # 实例 A：偏向 CVE 检索 [1.0, 0.0]
    # 实例 B：偏向 ATT&CK 推理 [0.0, 1.0]
    # 任务特征向量 [0.9, 0.1] -> 应选 A
    a = GraphNode(node_id="cve_type", kind=NodeKind.Agent, capabilities=["recon"])
    b = GraphNode(node_id="attack_type", kind=NodeKind.Agent, capabilities=["recon"])
    result = elect(
        task_features=[0.9, 0.1],
        instances=[a, b],
        capability_vectors={
            "cve_type": [1.0, 0.0],
            "attack_type": [0.0, 1.0],
        },
    )
    assert result.node_id == "cve_type"


def test_elect_picks_other_when_features_flip():
    a = GraphNode(node_id="cve_type", kind=NodeKind.Agent, capabilities=["recon"])
    b = GraphNode(node_id="attack_type", kind=NodeKind.Agent, capabilities=["recon"])
    result = elect(
        task_features=[0.1, 0.9],
        instances=[a, b],
        capability_vectors={
            "cve_type": [1.0, 0.0],
            "attack_type": [0.0, 1.0],
        },
    )
    assert result.node_id == "attack_type"


def test_elect_single_instance():
    a = GraphNode(node_id="only", kind=NodeKind.Agent, capabilities=["recon"])
    result = elect(
        task_features=[1.0],
        instances=[a],
        capability_vectors={
            "only": [1.0],
        },
    )
    assert result.node_id == "only"
