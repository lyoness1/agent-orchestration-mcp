from unittest.mock import AsyncMock, patch

import pytest

from maestro.cli import DEFAULT_QUESTION, main
from maestro.llm import MissingApiKeyError
from maestro.models import Report
from maestro.orchestrator import Orchestrator
from maestro.settings import Settings


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


def test_main_without_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("maestro.llm.settings", Settings(ANTHROPIC_API_KEY=None))

    with pytest.raises(MissingApiKeyError):
        main(["What", "is", "MCP?"])
