"""Shared helpers for MCP client and orchestrator integration tests."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
import httpx
from mcp import StdioServerParameters

from maestro.mcp_client import MaestroMcpClient
from maestro.mcp_server.server import mcp as maestro_mcp_server


def server_params() -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=["-m", "maestro.mcp_server"])


def mock_response(
    *,
    status_code: int = 200,
    text: str = "",
    content_type: str = "text/html; charset=utf-8",
    url: str = "https://example.com/page",
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(
        status_code,
        text=text,
        headers={"content-type": content_type},
        request=request,
    )


@asynccontextmanager
async def in_process_client() -> AsyncIterator[MaestroMcpClient]:
    """Connect MaestroMcpClient to maestro-mcp in-process over memory streams.

    Production spawns the server as a subprocess (``stdio_client``), which runs in
    a separate Python process. ``@patch`` on ``fetch_url.httpx.Client`` only affects
    the test process, so mocks would not reach a real subprocess.

    This fixture runs the FastMCP server loop in a background task and cross-wires
    two anyio memory stream pairs so client and server exchange the same
    ``SessionMessage`` JSON-RPC frames they would over stdin/stdout — without
    spawning. ``MaestroMcpClient(streams=...)`` skips ``stdio_client`` and uses
    those streams instead, so HTTP is mocked at the server layer while the full
    MCP client protocol path is still exercised.
    """
    client_read_send, client_read_recv = anyio.create_memory_object_stream(0)
    client_write_send, client_write_recv = anyio.create_memory_object_stream(0)

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            maestro_mcp_server._mcp_server.run,
            client_write_recv,
            client_read_send,
            maestro_mcp_server._mcp_server.create_initialization_options(),
        )
        async with MaestroMcpClient(streams=(client_read_recv, client_write_send)) as client:
            yield client
