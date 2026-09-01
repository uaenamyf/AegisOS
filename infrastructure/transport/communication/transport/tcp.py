# date: 2026-09-01
# dev: ox-alpha
"""受控 TCP Message transport，使用 JSON Lines 和异步接收队列。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from protocol import Message

from ..codecs import JsonCodec


class TcpTransport:
    """点对点 TCP 传输；默认只绑定调用方指定地址。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None
        self._received: asyncio.Queue[Message] = asyncio.Queue()
        self._connections: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
        """启动监听器并更新实际绑定端口。"""
        if self._server is not None:
            return
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        socket = self._server.sockets[0]
        self.port = int(socket.getsockname()[1])

    async def stop(self) -> None:
        """停止监听并关闭已建立连接。"""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in tuple(self._connections):
            writer.close()
            await writer.wait_closed()
        self._connections.clear()

    async def send(self, message: Message, host: str, port: int) -> bool:
        """向指定节点发送一条 Message。"""
        if message.ttl <= 0:
            return False
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(JsonCodec.encode(message))
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return True
        except (TimeoutError, ConnectionError, OSError):
            return False

    async def recv(self, timeout: float = 30.0) -> Message:
        """从接收队列读取一条 Message。"""
        return await asyncio.wait_for(self._received.get(), timeout=timeout)

    async def broadcast(
        self,
        message: Message,
        targets: list[tuple[str, int]],
        sender: Callable[[Message, str, int], Awaitable[bool]] | None = None,
    ) -> int:
        """仅向显式 targets 发送，返回成功数，不执行全网发现。"""
        if message.ttl <= 0:
            return 0
        send_fn = sender or self.send
        results = await asyncio.gather(
            *(send_fn(message, host, port) for host, port in targets),
            return_exceptions=False,
        )
        return sum(results)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._connections.add(writer)
        try:
            while line := await reader.readline():
                self._received.put_nowait(JsonCodec.decode(line))
        except (ValueError, ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self._connections.discard(writer)
            writer.close()
            await writer.wait_closed()


__all__ = ["TcpTransport"]
