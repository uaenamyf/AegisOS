# date: 2026-09-01
# dev: ox-alpha
"""CVE 知识数据集：用小规模、可审计样本支撑离线攻防演示。"""

from __future__ import annotations

from protocol.cyber import Asset, VulnFinding

# 每条记录描述可匹配的服务、操作系统和攻击面；生产环境可替换为版本化导入器。
CVE_RECORDS: tuple[dict[str, object], ...] = (
    {
        "cve_id": "CVE-2021-44228",
        "keywords": ("java", "log4j", "ldap"),
        "os": ("",),
        "cvss": 10.0,
        "attack_surface": "java/log4j",
    },
    {
        "cve_id": "CVE-2021-26855",
        "keywords": ("exchange", "owa", "http"),
        "os": ("windows", ""),
        "cvss": 9.8,
        "attack_surface": "microsoft exchange",
    },
    {
        "cve_id": "CVE-2019-0708",
        "keywords": ("rdp", "remote desktop"),
        "os": ("windows",),
        "cvss": 9.8,
        "attack_surface": "rdp",
    },
    {
        "cve_id": "CVE-2021-34527",
        "keywords": ("print spooler", "spooler"),
        "os": ("windows",),
        "cvss": 8.2,
        "attack_surface": "windows print spooler",
    },
    {
        "cve_id": "CVE-2022-22965",
        "keywords": ("spring", "java"),
        "os": ("",),
        "cvss": 9.8,
        "attack_surface": "spring framework",
    },
    {
        "cve_id": "CVE-2023-34362",
        "keywords": ("moveit", "transfer"),
        "os": ("",),
        "cvss": 9.8,
        "attack_surface": "managed file transfer",
    },
)


def query_cves(assets: list[Asset]) -> list[VulnFinding]:
    """按资产服务和操作系统匹配本地 CVE 样本。

    匹配采用大小写不敏感的关键词包含关系；同一资产与 CVE 只返回一次。
    """
    findings: list[VulnFinding] = []
    for asset in assets:
        service_text = " ".join(asset.services).lower()
        os_text = asset.os.lower()
        for record in CVE_RECORDS:
            keywords = record["keywords"]
            operating_systems = record["os"]
            assert isinstance(keywords, tuple)
            assert isinstance(operating_systems, tuple)
            service_hit = any(str(keyword) in service_text for keyword in keywords)
            os_hit = any(not required or required in os_text for required in operating_systems)
            if not service_hit or not os_hit:
                continue
            cve_id = str(record["cve_id"])
            findings.append(
                VulnFinding(
                    finding_id=f"{asset.asset_id}:{cve_id}",
                    cve_id=cve_id,
                    asset_id=asset.asset_id,
                    cvss=float(record["cvss"]),
                    attack_surface=str(record["attack_surface"]),
                )
            )
    return findings


__all__ = ["CVE_RECORDS", "query_cves"]
