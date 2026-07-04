#!/usr/bin/env python3
# date: 2026-07-03
# dev: myf
# changelog: 剥离硬编码的前端本地类型块——生成器只产出 protocol 契约类型；前端本地类型改由 frontend/src/protocol/frontend-types.ts 手维护
"""从 protocol/ Python dataclass 生成 TypeScript 类型定义。

读取 `protocol` 包中所有导出类型，内省 dataclass 字段与枚举值，
随后将生成的 `.ts` 文件写入 `frontend/src/protocol/types.ts`。

本生成器只产出 protocol 契约类型；前端本地类型（ViewName、ConnectionStatus、
请求 DTO 等）由 frontend/src/protocol/frontend-types.ts 手工维护，
以保证单一数据源（SSOT）职责分离。

Usage:
    python3 tooling/scripts/gen_ts_types.py
"""

from __future__ import annotations

import dataclasses
import enum
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保能 import 到顶层 protocol 包
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import protocol  # noqa: E402  # 依赖上面的 sys.path 注入，故延迟导入并豁免 E402

# 生成产物输出路径：frontend/src/protocol/types.ts
OUTPUT = PROJECT_ROOT / "frontend" / "src" / "protocol" / "types.ts"

# --- Python → TS 类型映射辅助表 ---

# Python 基本类型名到 TS 类型名的映射表；用于处理无参数的裸类型注解
_PRIMITIVE_MAP = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "bytes": "string",  # bytes 在 TS 侧统一序列化为 string
    "Any": "any",
    "dict": "Record<string, any>",
    "list": "any[]",
    "object": "any",
}


def _py_type_to_ts(annotation, fallback: str = "any") -> str:
    """尽力将 Python 类型注解转换为 TypeScript 类型字符串。

    支持的注解形式：
    - None / NoneType -> "null"
    - list[T] / List[T] -> "T[]"
    - dict[K, V] -> "Record<string, any>"（忽略具体键值类型）
    - Optional[T] / Union[T, None] -> "T | null"
    - 裸基本类型（str/int/...）走 `_PRIMITIVE_MAP`
    - 嵌套 dataclass -> 其类名
    - Enum 子类 -> 其类名
    - 其余无法识别的注解返回 `fallback`。

    Args:
        annotation: Python 类型注解对象（来自 `typing.get_type_hints` 或
            `dataclasses.fields` 的 `.type` 字段）。
        fallback: 当无法识别注解时使用的回退 TS 类型字符串。

    Returns:
        对应的 TypeScript 类型字符串，如 `"string"`、`"Foo[]"`、
        `"Bar | null"` 等。
    """
    if annotation is None or annotation is type(None):
        return "null"

    origin = getattr(annotation, "__origin__", None)  # 泛型 origin，如 list/dict/Union
    args = getattr(annotation, "__args__", ())  # 泛型参数元组，如 (str,) 或 (str, NoneType)

    # list[T] -> T[]
    if origin is list:
        if args:
            inner = _py_type_to_ts(args[0])
            return f"{inner}[]"
        return "any[]"

    # dict[K, V] -> Record<string, any>（TS 侧不细化键值类型）
    if origin is dict:
        return "Record<string, any>"

    # Optional / Union —— 取非 None 分支并追加 | null
    import typing as _typing

    if origin is _typing.Union:
        non_none = [a for a in args if a is not type(None)]  # 过滤掉 NoneType
        if len(non_none) == 1:
            return f"{_py_type_to_ts(non_none[0])} | null"
        return "any"  # 多分支 Union 暂不细化，统一回退 any

    # 裸类型（str, int, ...）查映射表
    name = getattr(annotation, "__name__", str(annotation))
    if name in _PRIMITIVE_MAP:
        return _PRIMITIVE_MAP[name]

    # 嵌套 dataclass / protocol 类型：直接用类名引用
    if dataclasses.is_dataclass(annotation):
        return name

    # Enum 子类：用枚举类名作为 TS 类型名
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return annotation.__name__

    return fallback


def _generate_enum(ts_name: str, enum_cls: type) -> list[str]:
    """由 Python `(str, Enum)` 类生成 TS 联合类型定义行。

    Args:
        ts_name: 输出的 TypeScript 类型名。
        enum_cls: Python 枚举类对象。

    Returns:
        TS 源码行列表，形如 `["export type X = \"a\" | \"b\";", ""]`，
        末尾附带一个空行用于分隔后续定义。
    """
    values = []
    for member in enum_cls:
        val = member.value
        if isinstance(val, str):
            values.append(f'"{val}"')  # 字符串字面量加双引号
        else:
            values.append(str(val))  # 数值等直接转字符串
    union = " | ".join(values)
    return [f"export type {ts_name} = {union};", ""]


def _generate_interface(ts_name: str, cls: type) -> list[str]:
    """由 Python dataclass 生成 TS interface 定义行。

    Args:
        ts_name: 输出的 TypeScript interface 名。
        cls: 已被 `@dataclass` 装饰的 Python 类对象。

    Returns:
        TS 源码行列表，包含 `export interface ... { ... }` 及末尾空行。
    """
    lines = [f"export interface {ts_name} {{"]
    for f in dataclasses.fields(cls):
        ts_type = _py_type_to_ts(f.type)
        has_default = (
            f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
        )  # 有默认值或默认工厂的字段在 TS 侧标记为可选
        optional = "?" if has_default else ""
        lines.append(f"  {f.name}{optional}: {ts_type};")
    lines.append("}")
    lines.append("")
    return lines


def generate() -> str:
    """生成完整的 TS 文件内容字符串。

    流程：
    1. 拼装文件头注释（eslint/ts-nocheck 开关）。
    2. 遍历 `protocol.__all__`，将导出对象分类为 enum 与 dataclass 两组。
    3. 先输出 enum 联合类型，再输出 dataclass interface。

    Returns:
        可直接写入 `types.ts` 的完整源码字符串。
    """
    header = [
        "// date: 2026-06-27",
        "// dev: myf",
        "// changelog: 自动生成的 TypeScript 类型定义（由 tooling/scripts/gen_ts_types.py 生成，请勿手动编辑）",
        "",
        "/* eslint-disable */",
        "// @ts-nocheck",
        "// This file is auto-generated from protocol/*.py — DO NOT EDIT MANUALLY.",
        "// Run `python3 tooling/scripts/gen_ts_types.py` or `npm run gen:types` to regenerate.",
        "",
    ]

    enums: list[tuple[str, type]] = []  # 收集 (类型名, 枚举类)
    dataclasses_list: list[tuple[str, type]] = []  # 收集 (类型名, dataclass 类)

    # 按名字排序遍历，保证生成产物稳定可 diff
    for name in sorted(protocol.__all__):
        obj = getattr(protocol, name)
        if isinstance(obj, type) and issubclass(obj, enum.Enum):
            enums.append((name, obj))
        elif dataclasses.is_dataclass(obj):
            dataclasses_list.append((name, obj))

    body: list[str] = []
    body.append("// === Enums / Union types ===")
    body.append("")
    for ts_name, cls in enums:
        body.extend(_generate_enum(ts_name, cls))

    body.append("// === Interfaces ===")
    body.append("")
    for ts_name, cls in dataclasses_list:
        body.extend(_generate_interface(ts_name, cls))

    # 说明：前端本地类型（ViewName、ConnectionStatus、ApiError、Session、
    # 请求 DTO 等）曾经硬编码在此处。现已迁移到
    # frontend/src/protocol/frontend-types.ts 手工维护，本生成器只产出
    # protocol/ 契约类型，以实现单一数据源（SSOT）职责分离。

    return "\n".join(header + body)


def main() -> None:
    """脚本入口：生成 TS 类型文件并打印统计信息。

    会创建输出目录（若不存在），写入 `types.ts`，并在 stdout 输出
    生成的 enum 与 interface 数量。
    """
    content = generate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)  # 确保输出目录存在
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"TypeScript types generated: {OUTPUT}")
    print(
        f"  enums: {sum(1 for n in protocol.__all__ if isinstance(getattr(protocol, n), type) and issubclass(getattr(protocol, n), enum.Enum))}"
    )  # 统计导出的枚举数量
    print(
        f"  interfaces: {sum(1 for n in protocol.__all__ if dataclasses.is_dataclass(getattr(protocol, n)))}"
    )  # 统计导出的 dataclass 数量


if __name__ == "__main__":
    main()
