"""Coordinates the agent pipeline that answers a question."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from maestro.mcp_client import MaestroMcpClient, default_mcp_client_factory
from maestro.models import Report

PROBE_URL = "https://example.com/"

McpClientFactory = Callable[[], AbstractAsyncContextManager[MaestroMcpClient]]


class Orchestrator:
    """Runs the agent pipeline end to end."""

    def __init__(
        self,
        *,
        mcp_client_factory: McpClientFactory = default_mcp_client_factory,
    ) -> None:
        self._mcp_client_factory = mcp_client_factory

    async def run(self, question: str) -> Report:
        """Answer ``question`` and return the resulting Report."""
        async with self._mcp_client_factory() as mcp:
            summary = await mcp.fetch_url(PROBE_URL)
            return Report(question=question, summary=summary)
