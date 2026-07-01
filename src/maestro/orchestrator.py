"""Coordinates the agent pipeline that answers a question."""

from maestro.mcp_client import MaestroMcpClient
from maestro.models import Report

# Temporary probe URL until the Researcher agent owns web retrieval (Slice 5).
_PROBE_URL = "https://example.com/"


class Orchestrator:
    """Runs the agent pipeline end to end.

    v1 fetches one page via MCP and puts the text in the report summary. Planner,
    Researcher, Analyst, and Editor replace this path in later slices.
    """

    async def run(self, question: str, *, mcp_client: MaestroMcpClient | None = None) -> Report:
        """Answer ``question`` and return the resulting Report."""
        if mcp_client is not None:
            return await self._run_with_mcp(question, mcp_client)
        async with MaestroMcpClient() as client:
            return await self._run_with_mcp(question, client)

    async def _run_with_mcp(self, question: str, mcp: MaestroMcpClient) -> Report:
        summary = await mcp.fetch_url(_PROBE_URL)
        return Report(question=question, summary=summary)
