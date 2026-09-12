# date: 2026-09-01
# dev: ox-alpha
"""本地 CVE 知识数据集与资产匹配查询。"""

from .knowledge import CVE_RECORDS, query_cves

__all__ = ["CVE_RECORDS", "query_cves"]
