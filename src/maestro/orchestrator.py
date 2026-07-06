"""Coordinates the agent pipeline that answers a question."""

from __future__ import annotations

from maestro.agents import researcher
from maestro.llm import LlmFactory, default_llm_factory
from maestro.mcp_client import McpClientFactory, default_mcp_client_factory
from maestro.models import PlanItem, Report, ResearchPlan, ResearchSources


def stub_research_plan(question: str) -> ResearchPlan:
    """Build a one-item plan until an LLM Planner replaces this stub."""
    return ResearchPlan(question=question, items=(PlanItem(subtopic=question),))


def research_sources_to_report(sources: ResearchSources) -> Report:
    """Turn research sources into a readable report for the CLI.

    Answer comes from the model's final turn; sources list URLs with citation keys.
    """
    if not sources.sources:
        return Report(
            question=sources.question,
            summary="No web pages were retrieved.",
            sources=(),
        )

    answer = sources.answer or "Research finished, but the model did not return text."
    bibliography = tuple(f"[{s.citation_key}] {s.url}" for s in sources.sources)
    return Report(question=sources.question, summary=answer, sources=bibliography)


class Orchestrator:
    """Runs the agent pipeline end to end."""

    def __init__(
        self,
        *,
        mcp_client_factory: McpClientFactory = default_mcp_client_factory,
        llm_factory: LlmFactory = default_llm_factory,
    ) -> None:
        self._mcp_client_factory = mcp_client_factory
        self._llm_factory = llm_factory

    async def run(self, question: str) -> Report:
        """Answer ``question`` and return the resulting Report."""
        plan = stub_research_plan(question)
        llm = self._llm_factory()
        async with self._mcp_client_factory() as mcp:
            sources = await researcher.research(plan, mcp, llm)
        return research_sources_to_report(sources)
