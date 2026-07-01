import asyncio

from maestro.models import Report
from maestro.orchestrator import Orchestrator


def test_run_returns_empty_report_for_question() -> None:
    report = asyncio.run(Orchestrator().run("What is MCP?"))

    assert isinstance(report, Report)
    assert report.question == "What is MCP?"
    assert report.summary == ""
    assert report.sources == ()
