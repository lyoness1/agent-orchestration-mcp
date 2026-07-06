import asyncio
from unittest.mock import MagicMock

from maestro.llm_mock_responses import EXAMPLE_URL, RESEARCH_ANSWER
from maestro.models import Report, ResearchSources, Source
from maestro.orchestrator import Orchestrator, research_sources_to_report, stub_research_plan
from mcp_test_helpers import mock_response


def test_stub_research_plan_wraps_question() -> None:
    plan = stub_research_plan("What is MCP?")

    assert plan.question == "What is MCP?"
    assert len(plan.items) == 1
    assert plan.items[0].subtopic == "What is MCP?"


def test_run_delegates_to_researcher_and_builds_report(
    orchestrator: Orchestrator, mock_fetch_http: MagicMock
) -> None:
    report = asyncio.run(orchestrator.run("What is MCP?"))

    assert isinstance(report, Report)
    assert report.question == "What is MCP?"
    assert report.summary == RESEARCH_ANSWER
    assert report.sources == (f"[ref-1] {EXAMPLE_URL}",)
    mock_fetch_http.get.assert_called_once_with(EXAMPLE_URL)


def test_run_surfaces_fetch_errors(orchestrator: Orchestrator, mock_fetch_http: MagicMock) -> None:
    mock_fetch_http.get.return_value = mock_response(
        status_code=404,
        text="Not Found",
        url=EXAMPLE_URL,
    )

    report = asyncio.run(orchestrator.run("What is MCP?"))

    assert report.summary == RESEARCH_ANSWER
    assert report.sources == (f"[ref-1] {EXAMPLE_URL}",)


def test_research_sources_to_report_with_sources() -> None:
    sources = ResearchSources(
        question="What is MCP?",
        sources=(
            Source(
                citation_key="ref-1",
                url="https://example.com/",
                excerpt="Example Domain is for documentation examples.",
                tool="fetch_url",
            ),
        ),
        answer="MCP connects AI applications to external tools.",
    )

    report = research_sources_to_report(sources)

    assert report.question == "What is MCP?"
    assert report.summary == "MCP connects AI applications to external tools."
    assert report.sources == ("[ref-1] https://example.com/",)


def test_research_sources_to_report_empty_sources() -> None:
    sources = ResearchSources(question="What is MCP?", sources=())

    report = research_sources_to_report(sources)

    assert report.question == "What is MCP?"
    assert report.summary == "No web pages were retrieved."
    assert report.sources == ()
