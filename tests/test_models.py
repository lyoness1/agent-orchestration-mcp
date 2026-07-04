from maestro.models import PlanItem, Report, ResearchPlan, ResearchSources, Source


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


def test_research_plan_holds_items() -> None:
    plan = ResearchPlan(
        question="What is MCP?",
        items=(
            PlanItem(subtopic="MCP basics"),
            PlanItem(subtopic="MCP vs function calling", search_queries=("MCP protocol",)),
        ),
    )

    assert plan.question == "What is MCP?"
    assert len(plan.items) == 2
    assert plan.items[1].search_queries == ("MCP protocol",)


def test_research_sources_holds_sources() -> None:
    source = Source(
        citation_key="ref-1",
        url="https://example.com/docs",
        excerpt="Example Domain is for documentation examples.",
        tool="fetch_url",
    )
    sources = ResearchSources(question="What is example.com?", sources=(source,))

    assert sources.question == "What is example.com?"
    assert len(sources.sources) == 1
    assert sources.sources[0].citation_key == "ref-1"
