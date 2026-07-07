"""Coordinates the agent pipeline that answers a question."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from maestro.agents.researcher import research
from maestro.llm import LlmClient
from maestro.mcp_client import MaestroMcpClient, default_mcp_client_factory
from maestro.models import Report

McpClientFactory = Callable[[], AbstractAsyncContextManager[MaestroMcpClient]]


class Orchestrator:
    """Runs the agent pipeline end to end."""

    def __init__(
        self,
        *,
        mcp_client_factory: McpClientFactory = default_mcp_client_factory,
        llm: LlmClient | None = None,
    ) -> None:
        # A factory, not an instance, because each run needs a fresh MCP subprocess
        # session (spawned on enter, torn down on exit); the LlmClient is reusable.
        self._mcp_client_factory = mcp_client_factory
        self._llm = llm or LlmClient()

    async def run(self, question: str) -> Report:
        """Answer ``question`` and return the resulting Report."""
        async with self._mcp_client_factory() as mcp:
            summary = await research(question, mcp, self._llm)
        return Report(question=question, summary=summary)
