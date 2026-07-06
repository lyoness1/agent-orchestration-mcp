from unittest.mock import AsyncMock, patch

import pytest

from maestro.cli import DEFAULT_QUESTION, main
from maestro.models import Report
from maestro.orchestrator import Orchestrator


@patch.object(Orchestrator, "run", new_callable=AsyncMock)
def test_main_with_question_prints_report(
    mock_run: AsyncMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_run.return_value = Report(question="What is MCP?", summary="MCP connects LLMs to tools.")
    exit_code = main(["What", "is", "MCP?"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Question: What is MCP?" in out
    assert "Answer:" in out
    assert "MCP connects LLMs to tools." in out


@patch.object(Orchestrator, "run", new_callable=AsyncMock)
def test_main_without_question_uses_fallback(
    mock_run: AsyncMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_run.return_value = Report(question=DEFAULT_QUESTION, summary="A default answer.")
    exit_code = main([])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert f"Question: {DEFAULT_QUESTION}" in out
