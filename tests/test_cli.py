from unittest.mock import AsyncMock, patch

import pytest

from maestro.cli import DEFAULT_QUESTION, main
from maestro.llm import API_KEY_ENV, MissingApiKeyError
from maestro.models import Report
from maestro.orchestrator import Orchestrator


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a key so the CLI runs; Orchestrator.run is mocked, so it is never used."""
    monkeypatch.setenv(API_KEY_ENV, "test-key-not-used")


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


def test_main_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # The CLI no longer gates on the key; the missing key surfaces when the
    # Orchestrator builds its LlmClient. This exits the process (does not hang).
    monkeypatch.delenv(API_KEY_ENV, raising=False)

    with pytest.raises(MissingApiKeyError):
        main(["What", "is", "MCP?"])
