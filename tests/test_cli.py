from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maestro.cli import DEFAULT_QUESTION, main
from maestro.llm import MissingApiKeyError
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


@patch("maestro.cli.load_env")
def test_main_without_api_key_raises(
    _mock_load_env: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Skip .env loading so an empty key is not replaced by a local .env file.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    with pytest.raises(MissingApiKeyError):
        main(["What", "is", "MCP?"])
