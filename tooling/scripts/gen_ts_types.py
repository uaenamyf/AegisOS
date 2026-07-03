#!/usr/bin/env python3
# @aegis-gen
# date: 2026-07-03
# dev: Claude Code (glm-5.2)
# change: 剥离硬编码的前端本地类型块——生成器只产出 protocol 契约类型；前端本地类型改由 frontend/src/protocol/frontend-types.ts 手维护
# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 gen_ts_types.py，由 protocol/ dataclass 类型生成 TypeScript 类型定义到 frontend/src/protocol/types.ts
"""Generate TypeScript type definitions from protocol/ Python dataclasses.

Reads all exported types from the `protocol` package, introspects dataclass
fields and enum values, and writes a `.ts` file to
`frontend/src/protocol/types.ts`.

Usage:
    python3 tooling/scripts/gen_ts_types.py
"""

from __future__ import annotations

import dataclasses
import enum
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import protocol  # noqa: E402

OUTPUT = PROJECT_ROOT / "frontend" / "src" / "protocol" / "types.ts"

# --- Python → TS type mapping helpers ---

_PRIMITIVE_MAP = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "bytes": "string",
    "Any": "any",
    "dict": "Record<string, any>",
    "list": "any[]",
    "object": "any",
}


def _py_type_to_ts(annotation, fallback: str = "any") -> str:
    """Best-effort conversion of a Python type annotation to a TS type string."""
    if annotation is None or annotation is type(None):
        return "null"

    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    # list[T]
    if origin is list:
        if args:
            inner = _py_type_to_ts(args[0])
            return f"{inner}[]"
        return "any[]"

    # dict[K, V]
    if origin is dict:
        return "Record<string, any>"

    # Optional / Union — pick non-None member and add | null
    import typing as _typing

    if origin is _typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return f"{_py_type_to_ts(non_none[0])} | null"
        return "any"

    # Bare types (str, int, ...)
    name = getattr(annotation, "__name__", str(annotation))
    if name in _PRIMITIVE_MAP:
        return _PRIMITIVE_MAP[name]

    # Nested dataclass / protocol type
    if dataclasses.is_dataclass(annotation):
        return name

    # Enum
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return annotation.__name__

    return fallback


def _generate_enum(ts_name: str, enum_cls: type) -> list[str]:
    """Generate a TS union type from a Python (str, Enum) class."""
    values = []
    for member in enum_cls:
        val = member.value
        if isinstance(val, str):
            values.append(f'"{val}"')
        else:
            values.append(str(val))
    union = " | ".join(values)
    return [f"export type {ts_name} = {union};", ""]


def _generate_interface(ts_name: str, cls: type) -> list[str]:
    """Generate a TS interface from a Python dataclass."""
    lines = [f"export interface {ts_name} {{"]
    for f in dataclasses.fields(cls):
        ts_type = _py_type_to_ts(f.type)
        has_default = (
            f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
        )
        optional = "?" if has_default else ""
        lines.append(f"  {f.name}{optional}: {ts_type};")
    lines.append("}")
    lines.append("")
    return lines


def generate() -> str:
    """Produce the full TS file content."""
    header = [
        "// @aegis-gen",
        "// date: 2026-06-27",
        "// dev: Claude Code (glm-5.2)",
        "// change: 自动生成的 TypeScript 类型定义（由 tooling/scripts/gen_ts_types.py 生成，请勿手动编辑）",
        "",
        "/* eslint-disable */",
        "// @ts-nocheck",
        "// This file is auto-generated from protocol/*.py — DO NOT EDIT MANUALLY.",
        "// Run `python3 tooling/scripts/gen_ts_types.py` or `npm run gen:types` to regenerate.",
        "",
    ]

    enums: list[tuple[str, type]] = []
    dataclasses_list: list[tuple[str, type]] = []

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

    # NOTE: frontend-local types (ViewName, ConnectionStatus, ApiError, Session,
    # request DTOs, ...) used to be hardcoded here. They are now hand-maintained
    # in frontend/src/protocol/frontend-types.ts so this generator emits ONLY the
    # protocol/ contract types (single source of truth separation).

    return "\n".join(header + body)


def main() -> None:
    content = generate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"TypeScript types generated: {OUTPUT}")
    print(
        f"  enums: {sum(1 for n in protocol.__all__ if isinstance(getattr(protocol, n), type) and issubclass(getattr(protocol, n), enum.Enum))}"
    )
    print(
        f"  interfaces: {sum(1 for n in protocol.__all__ if dataclasses.is_dataclass(getattr(protocol, n)))}"
    )


if __name__ == "__main__":
    main()
