"""R7 隐私分级分类器 —— 单元测试。

覆盖：强规则命中 local（IP/CVE/密钥/内网主机名）、弱规则累计、
默认 unrestricted、中文告警文本、攻击命令行、普通摘要请求。
"""

from __future__ import annotations

import pytest

from aegisos_agents.planning.engine.scheduler.privacy_classifier import (
    classify_privacy,
    classify_privacy_with_reason,
)


# ---------- 强规则：命中即 local（不能上云） ----------


def test_ipv4_address_is_local():
    text = "攻击来源 192.168.1.10 正在扫描内网端口 22"
    assert classify_privacy(text) == "local"


def test_ipv6_address_is_local():
    text = "连接 fe80::1 的目标主机"
    assert classify_privacy(text) == "local"


def test_cve_exploit_fragment_is_local():
    text = "curl -s --data @payload http://TARGET/cgi-bin/cmd CVE-2021-44228"
    assert classify_privacy(text) == "local"


def test_secret_key_keyword_is_local():
    text = "api_key=e2d45f8a91b3c7 用于签名请求"
    assert classify_privacy(text) == "local"


def test_internal_hostname_is_local():
    text = "连接内网主机 db-primary.corp.local 获取用户记录"
    assert classify_privacy(text) == "local"


# ---------- 弱规则：累计达阈值 → local ----------


def test_weak_rules_accumulate_to_local():
    # 内网主机名 + 数据库明文 + 用户名，多条弱规则应累计升 local
    text = "从 mysql 导出 uroot 的全部口令记录，来源是内网 dbserver"
    assert classify_privacy(text) == "local"


# ---------- 默认：unrestricted（可上云） ----------


def test_plain_summary_question_is_unrestricted():
    text = "请帮我总结一下这段新闻的主要观点"
    assert classify_privacy(text) == "unrestricted"


def test_empty_text_is_unrestricted():
    assert classify_privacy("") == "unrestricted"


def test_english_greeting_is_unrestricted():
    text = "Please write a haiku about autumn."
    assert classify_privacy(text) == "unrestricted"


# ---------- 中文告警 / 攻击相关 ----------


def test_chinese_alert_with_credential_hint_is_local():
    text = "系统检测到某主机尝试使用暴力枚举弱口令登录 10.0.0.5 的 SSH 服务"
    assert classify_privacy(text) == "local"


def test_personal_medical_data_hint_is_local():
    text = "该用户病历含身份证号 1101011990030787 与社保信息"
    assert classify_privacy(text) == "local"


# ---------- 显式语气不改变判定（关键词为准） ----------


def test_keyword_presence_trumps_claim_of_safety():
    # 即便声明"可公开"，命中密钥/内网词仍判 local（只升不降）
    text = "这个信息可公开，内网 token abc123 无影响"
    assert classify_privacy(text) == "local"


# ---------- R7 增强：classify_privacy_with_reason ----------


def test_with_reason_ip_returns_label():
    level, reason = classify_privacy_with_reason("攻击来源 192.168.1.10")
    assert level == "local"
    assert "IP地址" in reason


def test_with_reason_credential_returns_label():
    level, reason = classify_privacy_with_reason("password=admin123")
    assert level == "local"
    assert "凭据" in reason


def test_with_reason_unrestricted_returns_empty():
    level, reason = classify_privacy_with_reason("请总结这段文字")
    assert level == "unrestricted"
    assert reason == ""