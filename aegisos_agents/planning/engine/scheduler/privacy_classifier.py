# date: 2026-08-27
# dev: ox-alpha
"""数据敏感等级自动分级（R7 —— 端边云任务线）。

判读一段任务文本的隐私敏感度，决定它能否被派发到云侧执行。

三级语义（与 NodeProfile.PrivacyZone 对齐）：
    - local:          绝不能上云（IP/密钥/CVE 利用代码/内网主机名等强敏感）
    - unrestricted:   默认，可上云（普通摘要、提问等）

策略：**只升不降** —— 命中强规则即 local；弱规则累计达阈值升 local。
宁可本地多跑，不可泄露上云。

纯函数、无状态、可单测；规则表外置为模块常量（量小，YAGNI 不 yaml 化）。
"""

from __future__ import annotations

import re

# ---------------- 规则表 ----------------

# 强规则：命中任意一条即判 local（不能上云）
_STRONG_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?<!\d)(\d{1,3}\.){3}\d{1,3}(?!\d)"),              # IPv4
    re.compile(r"::"),                                             # IPv6 压缩形式 fe80::1
    re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I),                    # CVE 编号
    re.compile(r"\b(auth_token|bearer|password|passwd|secret|api[_-]?key|private_key|credential|token)\b", re.I),  # ASCII 凭据关键词
    re.compile(r"\b[\w.-]+\.corp\.(local|lan|com)\b", re.I),      # 内网主机名
    re.compile(r"\b(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)"),  # 私有网段
    re.compile(r"\d{17}[\dXx]|\d{15}"),                            # 身份证号 18/15 位
]

# 强规则（中文，不用 \b 词边界——Python 对 CJK 的 \b 不可靠）：命中即 local
_STRONG_CJK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"身份证号?|口令|密码|密钥|令牌|社保|病历|银行卡|凭证"),
]

# 弱规则：(pattern, weight) —— 中英分开，中文不用 \b
_WEAK_RULES: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\b(mysql|redis|mongo|oracle|ssh|sshkey|root|admin|system|username|user|account|uid)\b", re.I), 1),
    (re.compile(r"内网|局域网|数据中台|用户表|数据库|明文|登录名|用户名|账号"), 2),
    (re.compile(r"手机号|住址|地址|体检|医保"), 2),
]

_WEAK_THRESHOLD = 3

# ---------------- 分级 ----------------

def classify_privacy(text: str) -> str:
    """判读文本隐私等级，返回 ``local`` 或 ``unrestricted``。

    Args:
        text: 待判读的任务/告警/请求文本。

    Returns:
        ``local``（强敏感，不上云）或 ``unrestricted``（可上云）。
    """
    if not text:
        return "unrestricted"

    # 强规则：命中即 local
    for pattern in _STRONG_PATTERNS + _STRONG_CJK_PATTERNS:
        if pattern.search(text):
            return "local"

    # 弱规则：累计计分
    score = 0
    for pattern, weight in _WEAK_RULES:
        if pattern.search(text):
            score += weight

    return "local" if score >= _WEAK_THRESHOLD else "unrestricted"


__all__ = ["classify_privacy"]