"""工具协议类型。

定义 Agent 工具调用的数据契约，包括调用请求、返回结果与
工具规格描述，是工具注册与调用的基础类型层。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """工具调用请求。

    描述 Agent 对工具发起的一次调用。

    Attributes:
        call_id: 调用唯一标识，自动生成 UUID hex。
        name: 工具名称。
        args: 调用参数字典。
        timeout: 超时时间（秒）。
        permission: 权限要求标识。
    """

    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    args: dict = field(default_factory=dict)
    timeout: float = 30.0
    permission: str = ""


@dataclass
class ToolResult:
    """工具调用结果。

    描述工具调用的返回结果。

    Attributes:
        call_id: 对应的调用 ID。
        ok: 是否调用成功。
        output: 调用输出，类型不限。
        error: 错误信息，成功时为空。
        meta: 附加元信息（如执行耗时）。
    """

    call_id: str = ""
    ok: bool = True
    output: object = None
    error: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class ToolSpec:
    """工具规格描述。

    描述工具的元信息，用于工具注册与能力发现。

    Attributes:
        name: 工具名称。
        description: 工具功能描述。
        args_schema: 参数 schema，描述参数类型与约束。
        output_schema: 输出 schema，描述返回值结构。
        permission: 默认权限要求。
        resource_limit: 资源限制（如内存、调用频率）。
    """

    name: str
    description: str = ""
    args_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    permission: str = "default"
    resource_limit: dict = field(default_factory=dict)
