from maestro.models import Report


def test_render_includes_question_and_placeholders() -> None:
    text = Report(question="What is MCP?").render()

    assert "Question: What is MCP?" in text
    assert "(no summary yet)" in text
    assert "(none yet)" in text


def test_render_lists_sources() -> None:
    report = Report(
        question="What is MCP?",
        summary="A short summary.",
        sources=("https://a.example", "https://b.example"),
    )

    text = report.render()

    assert "A short summary." in text
    assert "- https://a.example" in text
    assert "- https://b.example" in text
