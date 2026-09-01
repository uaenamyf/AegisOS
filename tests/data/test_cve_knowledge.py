# date: 2026-09-01
# dev: ox-alpha
"""CVE 离线数据集与资产匹配查询测试。"""

from data.api import query_cves
from data.datasets.cve import CVE_RECORDS
from protocol.cyber import Asset, VulnFinding


def test_cve_dataset_contains_auditable_samples() -> None:
    assert len(CVE_RECORDS) >= 5
    assert {str(record["cve_id"]) for record in CVE_RECORDS} >= {
        "CVE-2021-44228",
        "CVE-2019-0708",
    }


def test_query_cves_matches_service_and_operating_system() -> None:
    findings = query_cves(
        [
            Asset(
                asset_id="win-rdp-01",
                host="10.0.0.10",
                services=["RDP", "SMB"],
                os="Windows Server 2019",
            )
        ]
    )
    assert [finding.cve_id for finding in findings] == ["CVE-2019-0708"]
    assert all(isinstance(finding, VulnFinding) for finding in findings)


def test_query_cves_matches_java_without_os_restriction() -> None:
    findings = query_cves(
        [Asset(asset_id="app-01", host="10.0.0.20", services=["Java", "Log4j"])]
    )
    assert any(finding.cve_id == "CVE-2021-44228" for finding in findings)


def test_query_cves_returns_empty_for_unknown_asset() -> None:
    assert query_cves([Asset(asset_id="safe-01", services=["ssh"], os="Linux")]) == []
