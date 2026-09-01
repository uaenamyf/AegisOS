# date: 2026-09-01
# dev: ox-alpha
"""基于 JSON Lines 的 protocol.Message 编解码。"""

from __future__ import annotations

import json

from protocol import Message


class JsonCodec:
    """将 Message 编码为单行 JSON，并严格解码回 Message。"""

    @staticmethod
    def encode(message: Message) -> bytes:
        """编码一条消息，返回带换行符的 UTF-8 字节。"""
        if not isinstance(message, Message):
            raise TypeError("communication payload must be protocol.Message")
        return (json.dumps(message.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )

    @staticmethod
    def decode(data: bytes) -> Message:
        """解码一行 JSON；格式非法时抛出 ValueError。"""
        try:
            value = json.loads(data.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("message JSON must be an object")
            return Message.from_dict(value)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            raise ValueError("invalid Message JSON") from exc
