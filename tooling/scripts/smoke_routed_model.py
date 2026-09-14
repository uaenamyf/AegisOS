# R20 路由决策冒烟(带后端 infra registry):模拟后端进程内完整链路
import os

os.environ.setdefault("AEGIS_USE_MOCK", "false")
os.environ.setdefault("OPENAI_API_KEY", "placeholder")

from backend.main import _init_infra_service

_init_infra_service()

from aegisos_agents.tools.llms.sdk_provider import SDKProvider

p = SDKProvider(enable_routing=True)
m = p.get_sdk_model()
assert type(m).__name__ == "RoutedSDKModel", type(m).__name__
for agent in ["recon", "exploit_planner", "detector", "critic"]:
    m.set_agent(agent)
    d = m._decide()
    tier = d.get("tier")
    node = d.get("node_id")
    model = d.get("model_id")
    reason = str(d.get("reason"))[:66]
    print(f"{agent:18s} -> {tier:6s} node={node} model={model} | {reason}")
print("OK")
