"""Coordinates the agent pipeline that answers a question."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from maestro.agents import researcher
from maestro.mcp_client import MaestroMcpClient, default_mcp_client_factory
from maestro.models import PlanItem, Report, ResearchPlan, ResearchSources

McpClientFactory = Callable[[], AbstractAsyncContextManager[MaestroMcpClient]]


def stub_research_plan(question: str) -> ResearchPlan:
    """Build a one-item plan until an LLM Planner replaces this stub."""
    return ResearchPlan(question=question, items=(PlanItem(subtopic=question),))


def research_sources_to_report(sources: ResearchSources) -> Report:
    """Turn research sources into a report summary and bibliography.

    Temporary shaping until Editor exists: summary is raw excerpts with citation
    keys, not synthesized prose.
    """
    if not sources.sources:
        return Report(question=sources.question, summary="(no sources retrieved)")

    parts = [
        f"[{source.citation_key}] {source.url}\n{source.excerpt}" for source in sources.sources
    ]
    return Report(
        question=sources.question,
        summary="\n\n".join(parts),
        sources=tuple(source.url for source in sources.sources),
    )


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
        plan = stub_research_plan(question)
        async with self._mcp_client_factory() as mcp:
            sources = await researcher.research(plan, mcp)
        return research_sources_to_report(sources)
