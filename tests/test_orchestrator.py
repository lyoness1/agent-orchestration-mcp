import asyncio
from unittest.mock import MagicMock

from maestro.constants import PROBE_URL
from maestro.models import Report, ResearchSources, Source
from maestro.orchestrator import Orchestrator, research_sources_to_report, stub_research_plan
from mcp_test_helpers import DEFAULT_PAGE_TEXT, mock_response


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
    assert report.summary.startswith(f"[ref-1] {PROBE_URL}")
    assert DEFAULT_PAGE_TEXT in report.summary
    assert report.sources == (PROBE_URL,)
    mock_fetch_http.get.assert_called_once_with(PROBE_URL)


def test_run_surfaces_fetch_errors(orchestrator: Orchestrator, mock_fetch_http: MagicMock) -> None:
    mock_fetch_http.get.return_value = mock_response(
        status_code=404,
        text="Not Found",
        url=PROBE_URL,
    )

    report = asyncio.run(orchestrator.run("What is MCP?"))

    assert f"[ref-1] {PROBE_URL}" in report.summary
    assert report.summary.endswith(f"Error: {PROBE_URL} returned HTTP 404.")
    assert report.sources == (PROBE_URL,)


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
    )

    report = research_sources_to_report(sources)

    assert report.question == "What is MCP?"
    assert report.summary == (
        "[ref-1] https://example.com/\nExample Domain is for documentation examples."
    )
    assert report.sources == ("https://example.com/",)


def test_research_sources_to_report_empty_sources() -> None:
    sources = ResearchSources(question="What is MCP?", sources=())

    report = research_sources_to_report(sources)

    assert report.question == "What is MCP?"
    assert report.summary == "(no sources retrieved)"
    assert report.sources == ()
