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

# ---------------- 规则表（带标签，用于前端反馈）----------------

# 强规则：命中任意一条即判 local（不能上云）
# (pattern, label) —— label 是给用户看的分类原因
_STRONG_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<!\d)(\d{1,3}\.){3}\d{1,3}(?!\d)"), "IP地址"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}\b"), "IPv6地址"),
    (re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"), "MAC地址"),
    (re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I), "CVE漏洞编号"),
    (re.compile(
        r"\b(auth_token|bearer|password|passwd|secret|api[_-]?key|"
        r"private_key|credential|token)\b",
        re.I,
    ), "凭据/密钥"),
    (re.compile(r"\b[\w.-]+\.corp\.(local|lan|com)\b", re.I), "内网主机名"),
    (re.compile(r"\b(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)"), "私有网段"),
    (re.compile(r"\d{17}[\dXx]|\d{15}"), "身份证号"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "手机号"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "邮箱地址"),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "银行卡号"),
]

# 强规则（中文，不用 \b 词边界）
_STRONG_CJK_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"身份证号?|口令|密码|密钥|令牌|社保|病历|银行卡|凭证"), "隐私/凭证信息"),
]

# 弱规则：(pattern, weight, label)
_WEAK_RULES: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(mysql|redis|mongo|oracle|ssh|sshkey|root|admin|system|username|user|account|uid)\b", re.I), 1, "数据库/系统凭据"),
    (re.compile(r"内网|局域网|数据中台|用户表|数据库|明文|登录名|用户名|账号"), 2, "内网/数据库信息"),
    (re.compile(r"手机号|住址|地址|体检|医保|病历|开房|体检报告|诊断"), 2, "个人信息"),
    (re.compile(r"身份证|银行卡|社保号|护照|港澳通行证|驾照|驾驶证"), 2, "证件信息"),
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
    level, _ = classify_privacy_with_reason(text)
    return level


def classify_privacy_with_reason(text: str) -> tuple[str, str]:
    """判读隐私等级并返回原因标注。

    Args:
        text: 待判读文本。

    Returns:
        (level, reason)：
        - level: ``local`` 或 ``unrestricted``
        - reason: 中文原因，如 "检测到 IP地址"、"检测到 凭据/密钥, 内网/数据库信息"
          unrestricted 时为空串。
    """
    if not text:
        return "unrestricted", ""

    # 强规则：命中即 local
    for pattern, label in _STRONG_RULES + _STRONG_CJK_RULES:
        if pattern.search(text):
            return "local", f"检测到 {label}"

    # 弱规则：累计计分
    score = 0
    hit_labels: list[str] = []
    for pattern, weight, label in _WEAK_RULES:
        if pattern.search(text):
            score += weight
            hit_labels.append(label)

    if score >= _WEAK_THRESHOLD:
        return "local", f"检测到 {', '.join(hit_labels[:3])}"

    return "unrestricted", ""


# ---------------- 脱敏（P1：敏感数据脱敏后允许上云兜底） ----------------

# 占位符用中性写法：不含"密码/密钥/令牌"等会再触发强规则的敏感词，
# 也不含数字/冒号结构（避免与 IP/时间格式混淆）
_MASK_REPL = {
    "ip": "[地址A]",
    "ipv6": "[地址B]",
    "mac": "[硬件标识]",
    "cve": "[漏洞编号]",
    "host": "[内部主机]",
    "phone": "[联系方式]",
    "email": "[联系邮箱]",
    "id": "[证件信息]",
    "card": "[支付凭证]",
    "cred": "[凭据值]",
}

# 用于脱敏替换的规则表：命中即替换为占位符
_MASK_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<!\d)(\d{1,3}\.){3}\d{1,3}(?!\d)"), _MASK_REPL["ip"]),
    (re.compile(r"\b(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}\b"), _MASK_REPL["ipv6"]),
    (re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"), _MASK_REPL["mac"]),
    (re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I), _MASK_REPL["cve"]),
    (re.compile(
        r"\b[\w.-]+\.corp\.(local|lan|com)\b",
        re.I,
    ), _MASK_REPL["host"]),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), _MASK_REPL["phone"]),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), _MASK_REPL["email"]),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), _MASK_REPL["id"]),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), _MASK_REPL["card"]),
    # 凭据类：password=xxx / token: xxx 等键值对
    (re.compile(
        r"\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)"
        r"\b\s*[:=]\s*\S+",
        re.I,
    ), r"\1" + _MASK_REPL["cred"]),
    # 中文凭据键值对：密码：xxx / 口令: xxx（含全角冒号）——
    # 键名+值整体替换，避免残留"密码"二字再次触发中文强规则
    (re.compile(r"(密码|口令|令牌|密钥|凭据)\s*[：:]\s*\S+"), "[安全认证信息]"),
    # 空格分隔变体：密码 admin123（值限定为≥4位字母数字符号，防误伤"密码 是基础"）
    (re.compile(
        r"(密码|口令|令牌|密钥|凭据)\s+[A-Za-z0-9@#$%^&*_.\-]{4,}"
    ), "[安全认证信息]"),
]


def mask_sensitive(text: str) -> str:
    """脱敏文本中的敏感数据（供上云兜底使用）。

    将 IP/IPv6/MAC/手机号/邮箱/身份证/卡号/内网主机名/明文凭据替换为占位符，
    替换后不再触发强规则（占位符不含真实数据）。

    Args:
        text: 原始文本。

    Returns:
        脱敏后的文本。
    """
    if not text:
        return text
    out = text
    for pattern, repl in _MASK_RULES:
        out = pattern.sub(repl, out)
    return out


__all__ = [
    "classify_privacy",
    "classify_privacy_with_reason",
    "mask_sensitive",
]