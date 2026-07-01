import pytest

from maestro.cli import DEFAULT_QUESTION, main


def test_main_with_question_prints_report(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["What", "is", "MCP?"])

    # capsys is a pytest fixture that captures whatever was printed to stdout.
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Question: What is MCP?" in out
    assert "(no summary yet)" in out


def test_main_without_question_uses_fallback(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert f"Question: {DEFAULT_QUESTION}" in out
