# date: 2026-09-01
# dev: ox-alpha
"""TCP Message transport 与 JSON 编解码测试。"""

from __future__ import annotations

import pytest

from infrastructure.transport.communication.codecs import JsonCodec
from infrastructure.transport.communication.transport import TcpTransport
from protocol import Message, NodeRef


@pytest.mark.asyncio
async def test_tcp_roundtrip_preserves_message_envelope() -> None:
    receiver = TcpTransport()
    sender = TcpTransport()
    await receiver.start()
    try:
        message = Message(
            task_id="task-1",
            sender=NodeRef(node_id="device", node_type="device"),
            receiver=NodeRef(node_id="edge", node_type="edge"),
            payload={"event": "scan"},
        )
        assert await sender.send(message, "127.0.0.1", receiver.port)
        received = await receiver.recv(timeout=2)
        assert received.task_id == "task-1"
        assert received.payload == {"event": "scan"}
        assert received.sender.node_id == "device"
    finally:
        await receiver.stop()


def test_json_codec_rejects_non_message_payload() -> None:
    with pytest.raises(TypeError, match="protocol.Message"):
        JsonCodec.encode({"task_id": "bad"})  # type: ignore[arg-type]


def test_json_codec_roundtrip() -> None:
    message = Message(task_id="task-2", payload={"value": 1})
    assert JsonCodec.decode(JsonCodec.encode(message)).task_id == "task-2"


@pytest.mark.asyncio
async def test_tcp_rejects_expired_message() -> None:
    receiver = TcpTransport()
    sender = TcpTransport()
    await receiver.start()
    try:
        expired = Message(task_id="expired", ttl=0)
        assert await sender.send(expired, "127.0.0.1", receiver.port) is False
        with pytest.raises(TimeoutError):
            await receiver.recv(timeout=0.01)
    finally:
        await receiver.stop()


@pytest.mark.asyncio
async def test_broadcast_uses_only_explicit_targets() -> None:
    receiver = TcpTransport()
    sender = TcpTransport()
    await receiver.start()
    try:
        message = Message(task_id="broadcast", payload={"ok": True})
        count = await sender.broadcast(message, [("127.0.0.1", receiver.port)])
        assert count == 1
        assert (await receiver.recv(timeout=2)).task_id == "broadcast"
    finally:
        await receiver.stop()


@pytest.mark.asyncio
async def test_tcp_authentication_accepts_matching_token_and_rejects_other_token() -> None:
    receiver = TcpTransport(auth_token="demo-secret")
    sender = TcpTransport(auth_token="demo-secret")
    wrong = TcpTransport(auth_token="wrong-secret")
    await receiver.start()
    try:
        message = Message(task_id="authenticated")
        assert await sender.send(message, "127.0.0.1", receiver.port)
        assert (await receiver.recv(timeout=2)).task_id == "authenticated"
        assert await wrong.send(Message(task_id="rejected"), "127.0.0.1", receiver.port)
        with pytest.raises(TimeoutError):
            await receiver.recv(timeout=0.05)
    finally:
        await receiver.stop()


@pytest.mark.asyncio
async def test_tcp_retries_after_initial_connection_failure() -> None:
    receiver = TcpTransport(retry_attempts=4, retry_backoff_s=0.001)
    await receiver.start()
    try:
        sender = TcpTransport(retry_attempts=0)
        assert await sender.send(Message(task_id="retry"), "127.0.0.1", receiver.port)
        assert (await receiver.recv(timeout=2)).task_id == "retry"
    finally:
        await receiver.stop()
