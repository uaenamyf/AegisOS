# date: 2026-08-06
# dev: czy
"""ATT&CK 知识数据集 —— 技战术 + 关系边。

覆盖赛事 3 场景（侦察 / 横向移动 / 检测响应）所需技战术集合，
保留原始 8 条种子（T1595/T1592/T1210/T1059/T1078/T1046/T1021/T1053），
提供 :func:`load_attck_dataset` 供数据层与记忆子系统共享单一知识源。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket

# technique_id -> {name, tactic, platform, description}
ATTACK_TECHNIQUES: dict[str, dict[str, str]] = {
    # ---- reconnaissance（侦察）----
    "T1595": {
        "name": "Active Scanning",
        "tactic": "reconnaissance",
        "platform": "network",
        "description": "主动扫描目标收集可利用信息",
    },
    "T1592": {
        "name": "Gather Victim Host Info",
        "tactic": "reconnaissance",
        "platform": "network",
        "description": "收集目标主机配置/操作系统/软件信息",
    },
    "T1589": {
        "name": "Gather Victim Identity Info",
        "tactic": "reconnaissance",
        "platform": "identity",
        "description": "收集受害者身份信息（账号/组织）",
    },
    "T1590": {
        "name": "Gather Victim Network Info",
        "tactic": "reconnaissance",
        "platform": "network",
        "description": "收集目标网络拓扑/网段信息",
    },
    "T1598": {
        "name": "Phishing for Information",
        "tactic": "reconnaissance",
        "platform": "social",
        "description": "通过钓鱼收集目标情报",
    },
    "T1597": {
        "name": "Search Open Technical Databases",
        "tactic": "reconnaissance",
        "platform": "osint",
        "description": "在公开技术库中检索目标信息",
    },
    # ---- initial-access（初始访问）----
    "T1133": {
        "name": "External Remote Services",
        "tactic": "initial-access",
        "platform": "network",
        "description": "通过外部远程服务（VPN/RDP）进入内网",
    },
    "T1190": {
        "name": "Exploit Public-Facing Application",
        "tactic": "initial-access",
        "platform": "application",
        "description": "利用暴露在公网的应用程序漏洞获取访问",
    },
    "T1566": {
        "name": "Phishing",
        "tactic": "initial-access",
        "platform": "social",
        "description": "通过钓鱼邮件/链接诱导用户执行",
    },
    # ---- execution（执行）----
    "T1059": {
        "name": "Command and Scripting Interpreter",
        "tactic": "execution",
        "platform": "os",
        "description": "通过命令脚本解释器执行恶意代码",
    },
    "T1053": {
        "name": "Scheduled Task/Job",
        "tactic": "execution",
        "platform": "os",
        "description": "通过计划任务定时执行",
    },
    "T1204": {
        "name": "User Execution",
        "tactic": "execution",
        "platform": "user",
        "description": "诱导用户执行恶意文件",
    },
    "T1047": {
        "name": "Windows Management Instrumentation",
        "tactic": "execution",
        "platform": "windows",
        "description": "利用 WMI 执行远程命令",
    },
    "T1106": {
        "name": "Native API",
        "tactic": "execution",
        "platform": "os",
        "description": "直接调用系统原生 API 执行",
    },
    # ---- persistence（持久化）----
    "T1136": {
        "name": "Create Account",
        "tactic": "persistence",
        "platform": "os",
        "description": "创建本地/域账户维持访问",
    },
    "T1547": {
        "name": "Boot or Logon Autostart",
        "tactic": "persistence",
        "platform": "windows",
        "description": "利用开机/登录自启维持持久化",
    },
    "T1505": {
        "name": "Server Software Component",
        "tactic": "persistence",
        "platform": "server",
        "description": "在服务端软件注入后门组件",
    },
    # ---- defense-evasion（防御绕过）----
    "T1078": {
        "name": "Valid Accounts",
        "tactic": "defense-evasion",
        "platform": "identity",
        "description": "利用合法账户凭证规避检测",
    },
    "T1070": {
        "name": "Indicator Removal on Host",
        "tactic": "defense-evasion",
        "platform": "host",
        "description": "清除主机上的攻击痕迹与日志",
    },
    "T1036": {
        "name": "Masquerading",
        "tactic": "defense-evasion",
        "platform": "host",
        "description": "伪装成合法进程/文件名规避检测",
    },
    "T1027": {
        "name": "Obfuscated Files or Information",
        "tactic": "defense-evasion",
        "platform": "host",
        "description": "混淆恶意载荷与通信内容",
    },
    "T1562": {
        "name": "Impair Defenses",
        "tactic": "defense-evasion",
        "platform": "host",
        "description": "禁用或降低安全防护能力",
    },
    "T1140": {
        "name": "Deobfuscate/Decode Files or Information",
        "tactic": "defense-evasion",
        "platform": "host",
        "description": "解混淆/解码恶意文件还原载荷",
    },
    # ---- discovery（发现）----
    "T1046": {
        "name": "Network Service Discovery",
        "tactic": "discovery",
        "platform": "network",
        "description": "发现网络中可用的服务",
    },
    "T1016": {
        "name": "System Network Configuration Discovery",
        "tactic": "discovery",
        "platform": "host",
        "description": "获取本机网络配置信息",
    },
    "T1082": {
        "name": "System Information Discovery",
        "tactic": "discovery",
        "platform": "host",
        "description": "收集主机系统信息",
    },
    "T1087": {
        "name": "Account Discovery",
        "tactic": "discovery",
        "platform": "identity",
        "description": "枚举系统账户信息",
    },
    # ---- lateral-movement（横向移动）----
    "T1210": {
        "name": "Exploitation of Remote Services",
        "tactic": "lateral-movement",
        "platform": "network",
        "description": "利用远程服务漏洞进行横向移动",
    },
    "T1021": {
        "name": "Remote Services",
        "tactic": "lateral-movement",
        "platform": "network",
        "description": "通过远程服务（SSH/SMB/RDP）横向移动",
    },
    "T1550": {
        "name": "Use Alternate Authentication Material",
        "tactic": "lateral-movement",
        "platform": "identity",
        "description": "使用票据/哈希等替代认证材料横向移动",
    },
    "T1080": {
        "name": "Taint Shared Content",
        "tactic": "lateral-movement",
        "platform": "network",
        "description": "污染共享资源诱导横向执行",
    },
    # ---- collection（收集 / 蓝队关联）----
    "T1005": {
        "name": "Data from Local System",
        "tactic": "collection",
        "platform": "host",
        "description": "从本地系统收集敏感数据（检测重点）",
    },
}

# 关系边：(src, rel, dst)；rel ∈ contains/precedes/uses/targets
ATTACK_RELATIONS: list[tuple[str, str, str]] = [
    # tactic 包含
    ("reconnaissance", "contains", "T1595"),
    ("reconnaissance", "contains", "T1592"),
    ("reconnaissance", "contains", "T1589"),
    ("reconnaissance", "contains", "T1590"),
    ("reconnaissance", "contains", "T1598"),
    ("reconnaissance", "contains", "T1597"),
    ("initial-access", "contains", "T1133"),
    ("initial-access", "contains", "T1190"),
    ("initial-access", "contains", "T1566"),
    ("execution", "contains", "T1059"),
    ("execution", "contains", "T1053"),
    ("execution", "contains", "T1204"),
    ("execution", "contains", "T1047"),
    ("execution", "contains", "T1106"),
    ("persistence", "contains", "T1136"),
    ("persistence", "contains", "T1547"),
    ("persistence", "contains", "T1505"),
    ("defense-evasion", "contains", "T1078"),
    ("defense-evasion", "contains", "T1070"),
    ("defense-evasion", "contains", "T1036"),
    ("defense-evasion", "contains", "T1027"),
    ("defense-evasion", "contains", "T1562"),
    ("defense-evasion", "contains", "T1140"),
    ("discovery", "contains", "T1046"),
    ("discovery", "contains", "T1016"),
    ("discovery", "contains", "T1082"),
    ("discovery", "contains", "T1087"),
    ("lateral-movement", "contains", "T1210"),
    ("lateral-movement", "contains", "T1021"),
    ("lateral-movement", "contains", "T1550"),
    ("lateral-movement", "contains", "T1080"),
    ("collection", "contains", "T1005"),
    # 攻击链前置/使用关系
    ("T1595", "precedes", "T1592"),
    ("T1592", "precedes", "T1046"),
    ("T1046", "precedes", "T1190"),
    ("T1190", "precedes", "T1210"),
    ("T1210", "uses", "T1059"),
    ("T1566", "precedes", "T1204"),
    ("T1078", "uses", "T1021"),
    ("T1070", "targets", "T1005"),
]


def load_attck_dataset() -> list[MemoryPacket]:
    """将 ATT&CK 数据集转为 MemoryPacket 列表（供图存储 seed 与记忆子系统预载）。

    Returns:
        每条含 semantic 字段 technique_id/name/tactic/platform/description 的列表。
    """
    packets: list[MemoryPacket] = []
    for tid, info in ATTACK_TECHNIQUES.items():
        packets.append(
            MemoryPacket(
                task_id=tid,
                summary=f"{tid} {info['name']}",
                semantic={
                    "technique_id": tid,
                    "name": info["name"],
                    "tactic": info["tactic"],
                    "platform": info["platform"],
                    "description": info["description"],
                },
                kind="decision",
            )
        )
    return packets
