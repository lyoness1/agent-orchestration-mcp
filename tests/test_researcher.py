import asyncio
from unittest.mock import MagicMock

from maestro.agents.researcher import research
from maestro.llm_mock_responses import EXAMPLE_URL, RESEARCH_ANSWER, default_llm_factory
from maestro.models import PlanItem, ResearchPlan, ResearchSources
from mcp_test_helpers import DEFAULT_PAGE_TEXT, in_process_client, mock_response


def test_research_returns_research_sources(mock_fetch_http: MagicMock) -> None:
    plan = ResearchPlan(question="What is MCP?", items=(PlanItem(subtopic="What is MCP?"),))

    async def run() -> ResearchSources:
        async with in_process_client() as mcp:
            return await research(plan, mcp, default_llm_factory())

    sources = asyncio.run(run())

    assert isinstance(sources, ResearchSources)
    assert sources.question == "What is MCP?"
    assert len(sources.sources) == 1
    source = sources.sources[0]
    assert source.citation_key == "ref-1"
    assert source.url == EXAMPLE_URL
    assert source.tool == "fetch_url"
    assert DEFAULT_PAGE_TEXT in source.excerpt
    assert sources.answer == RESEARCH_ANSWER
    mock_fetch_http.get.assert_called_once_with(EXAMPLE_URL)


def test_research_processes_each_plan_item(mock_fetch_http: MagicMock) -> None:
    plan = ResearchPlan(
        question="Compare MCP and REST",
        items=(
            PlanItem(subtopic="MCP"),
            PlanItem(subtopic="REST"),
        ),
    )

    async def run() -> ResearchSources:
        async with in_process_client() as mcp:
            return await research(plan, mcp, default_llm_factory())

    sources = asyncio.run(run())

    assert sources.question == "Compare MCP and REST"
    assert len(sources.sources) == 2
    assert sources.sources[0].citation_key == "ref-1"
    assert sources.sources[1].citation_key == "ref-2"
    assert mock_fetch_http.get.call_count == 2


def test_research_surfaces_fetch_errors_in_excerpt(mock_fetch_http: MagicMock) -> None:
    mock_fetch_http.get.return_value = mock_response(
        status_code=404,
        text="Not Found",
        url=EXAMPLE_URL,
    )
    plan = ResearchPlan(question="What is MCP?", items=(PlanItem(subtopic="What is MCP?"),))

    async def run() -> ResearchSources:
        async with in_process_client() as mcp:
            return await research(plan, mcp, default_llm_factory())

    sources = asyncio.run(run())

    assert len(sources.sources) == 1
    assert sources.sources[0].excerpt == f"Error: {EXAMPLE_URL} returned HTTP 404."
