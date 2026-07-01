import asyncio
from unittest.mock import MagicMock, patch

from maestro.models import Report
from maestro.orchestrator import _PROBE_URL, Orchestrator
from mcp_test_helpers import in_process_client, mock_response


def test_run_returns_report_for_question() -> None:
    report = asyncio.run(Orchestrator().run("What is MCP?"))

    assert isinstance(report, Report)
    assert report.question == "What is MCP?"


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_run_fetches_probe_url_via_mcp(mock_client_cls: MagicMock) -> None:
    page_text = "Hello from MCP"
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response(
        text=f"<html><body><p>{page_text}</p></body></html>",
        url=_PROBE_URL,
    )

    async def run() -> Report:
        async with in_process_client() as client:
            return await Orchestrator().run("What is MCP?", mcp_client=client)

    report = asyncio.run(run())

    assert report.summary == page_text
    mock_client.get.assert_called_once_with(_PROBE_URL)
