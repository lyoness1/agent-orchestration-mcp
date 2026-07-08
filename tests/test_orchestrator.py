import asyncio
from typing import Any

from maestro.llm import ToolExecutor
from maestro.models import Report
from maestro.orchestrator import Orchestrator
from mcp_test_helpers import DEFAULT_PAGE_TEXT


class FakeLlm:
    """Test double that mimics one tool call followed by an answer."""

    async def run_tool_loop(
        self,
        *,
        system: str,
        prompt: str,
        tools: list[dict[str, Any]],
        execute_tool: ToolExecutor,
    ) -> str:
        _ = system
        _ = prompt
        _ = tools
        output = await execute_tool("fetch_url", {"url": "https://example.com/"})
        return f"Research complete: {output}"


def test_run_builds_report_from_research_results(in_process_mcp_factory) -> None:
    report = asyncio.run(
        Orchestrator(mcp_client_factory=in_process_mcp_factory, llm=FakeLlm()).run(
            "What is the Model Context Protocol?"
        )
    )

    assert isinstance(report, Report)
    assert report.question == "What is the Model Context Protocol?"
    assert report.summary == f"Research complete: {DEFAULT_PAGE_TEXT}"
    assert report.sources == ("https://example.com/",)
