# date: 2026-09-01
# dev: ox-alpha
"""Docker 交付与沙箱编排配置测试。"""

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[4]
DOCKER_DIR = ROOT / "infrastructure" / "delivery" / "deployment" / "docker"


def _load_compose(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_main_compose_has_health_dependency_and_explicit_secret() -> None:
    compose = _load_compose(DOCKER_DIR / "docker-compose.yml")
    backend = compose["services"]["backend"]
    frontend = compose["services"]["frontend"]

    assert backend["build"]["context"] == "../../../../"
    assert "AEGIS_AUTH_DEFAULT_KEY" in backend["environment"]
    assert frontend["depends_on"]["backend"]["condition"] == "service_healthy"
    assert frontend["ports"] == ["8080:80"]


def test_sandbox_has_no_host_ports_and_uses_internal_network() -> None:
    compose = _load_compose(DOCKER_DIR / "sandbox" / "docker-compose.yml")
    assert compose["networks"]["range"]["internal"] is True
    assert all("ports" not in service for service in compose["services"].values())
    assert compose["services"]["scanner"]["profiles"] == ["tools"]


def test_sandbox_services_use_container_hardening_defaults() -> None:
    compose = _load_compose(DOCKER_DIR / "sandbox" / "docker-compose.yml")
    for name in ("target-web", "target-db", "scanner", "metasploit", "zeek"):
        service = compose["services"][name]
        assert service["read_only"] is True
        assert "ALL" in service["cap_drop"]
        assert "no-new-privileges:true" in service["security_opt"]

    splunk = compose["services"]["splunk"]
    assert splunk["read_only"] is False
    assert "ALL" in splunk["cap_drop"]
    assert "no-new-privileges:true" in splunk["security_opt"]


def test_sandbox_tools_are_profiled_and_never_publish_ports() -> None:
    compose = _load_compose(DOCKER_DIR / "sandbox" / "docker-compose.yml")
    for name in ("scanner", "metasploit", "zeek", "splunk"):
        service = compose["services"][name]
        assert service["profiles"] == ["tools"]
        assert service["networks"] == ["range"]
        assert "ports" not in service
