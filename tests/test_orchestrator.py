import asyncio
from unittest.mock import MagicMock

from maestro.models import Report
from maestro.orchestrator import PROBE_URL
from mcp_test_helpers import DEFAULT_PAGE_TEXT, mock_response


def test_run_fetches_url_and_builds_report(orchestrator, mock_fetch_http: MagicMock) -> None:
    report = asyncio.run(orchestrator.run("What is MCP?"))

    assert isinstance(report, Report)
    assert report.question == "What is MCP?"
    assert report.summary == DEFAULT_PAGE_TEXT
    mock_fetch_http.get.assert_called_once_with(PROBE_URL)


def test_run_surfaces_fetch_errors(orchestrator, mock_fetch_http: MagicMock) -> None:
    mock_fetch_http.get.return_value = mock_response(
        status_code=404,
        text="Not Found",
        url=PROBE_URL,
    )

    report = asyncio.run(orchestrator.run("What is MCP?"))

    assert report.summary == f"Error: {PROBE_URL} returned HTTP 404."
