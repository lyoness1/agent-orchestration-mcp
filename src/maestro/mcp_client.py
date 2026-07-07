"""MCP client that spawns maestro-mcp and invokes its tools."""

from __future__ import annotations

import os
import shutil
import sys
from contextlib import AsyncExitStack
from typing import Self

import mcp.types as types
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.shared.message import SessionMessage

_SERVER_STDERR = open(os.devnull, "w")  # noqa: SIM115


def default_server_params() -> StdioServerParameters:
    """Return stdio parameters to launch the local maestro-mcp server."""
    if command := shutil.which("maestro-mcp"):
        return StdioServerParameters(command=command)
    return StdioServerParameters(command=sys.executable, args=["-m", "maestro.mcp_server"])


def default_mcp_client_factory() -> MaestroMcpClient:
    """Return a connected MCP client context manager for production use."""
    return MaestroMcpClient()


def _text_from_result(result: types.CallToolResult) -> str:
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            parts.append(block.text)
    return "\n".join(parts)


class MaestroMcpClient:
    """Spawn maestro-mcp over stdio and call its tools."""

    def __init__(
        self,
        server: StdioServerParameters | None = None,
        *,
        streams: tuple[
            MemoryObjectReceiveStream[SessionMessage | Exception],
            MemoryObjectSendStream[SessionMessage],
        ]
        | None = None,
    ) -> None:
        self._server_params = server or default_server_params()
        self._streams = streams
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def connect(self) -> None:
        """Start the MCP server subprocess and initialize the session."""
        if self._session is not None:
            return

        stack = AsyncExitStack()
        if self._streams is None:
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(self._server_params, errlog=_SERVER_STDERR)
            )
        else:
            read_stream, write_stream = self._streams
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        self._stack = stack
        self._session = session

    async def close(self) -> None:
        """Shut down the MCP session and terminate the server subprocess."""
        if self._stack is None:
            return

        await self._stack.aclose()
        self._stack = None
        self._session = None

    async def fetch_url(self, url: str) -> str:
        """Fetch a URL via the server's ``fetch_url`` tool."""
        session = self._require_session()
        result = await session.call_tool("fetch_url", {"url": url})
        return _text_from_result(result)

    def _require_session(self) -> ClientSession:
        if self._session is None:
            msg = "MCP client is not connected; use connect() or async with MaestroMcpClient()"
            raise RuntimeError(msg)
        return self._session
