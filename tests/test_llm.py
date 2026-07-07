import asyncio

import pytest

from maestro.llm import FETCH_URL_TOOL, LlmClient
from maestro.llm_mock_responses import EXAMPLE_URL, RESEARCH_ANSWER, default_llm_factory, fetch


def test_mock_client_first_call_requests_fetch() -> None:
    llm = default_llm_factory()

    first = llm.create_message(
        system="You are a research assistant.",
        messages=[{"role": "user", "content": "Research this subtopic: What is MCP?"}],
        tools=[FETCH_URL_TOOL],
    )

    assert first.stop_reason == "tool_use"
    assert first.tool_use_requests()[0]["input"]["url"] == EXAMPLE_URL


def test_mock_client_second_call_returns_end_turn() -> None:
    llm = default_llm_factory()
    llm.create_message(system="s", messages=[], tools=[])

    second = llm.create_message(system="s", messages=[], tools=[])

    assert second.stop_reason == "end_turn"
    assert second.text() == RESEARCH_ANSWER


def test_mock_client_increments_tool_ids_across_subtopics() -> None:
    llm = default_llm_factory()
    for expected_tool_id in ("toolu_1", "toolu_2"):
        fetch_turn = llm.create_message(system="s", messages=[], tools=[])
        done_turn = llm.create_message(system="s", messages=[], tools=[])
        assert fetch_turn.stop_reason == "tool_use"
        assert fetch_turn.tool_use_requests()[0]["id"] == expected_tool_id
        assert done_turn.stop_reason == "end_turn"


def test_researcher_loop_raises_after_max_turns() -> None:
    from unittest.mock import AsyncMock, MagicMock

    from maestro.agents.researcher import research
    from maestro.models import PlanItem, ResearchPlan

    # A script that only ever asks to fetch (never end_turn) forces the loop to hit
    # its turn cap.
    llm = LlmClient(replies=(fetch(EXAMPLE_URL, tool_id="toolu_seed"),))
    plan = ResearchPlan(question="What is MCP?", items=(PlanItem(subtopic="What is MCP?"),))
    mcp = MagicMock()
    mcp.fetch_url = AsyncMock(return_value="Example Domain")

    async def run() -> None:
        await research(plan, mcp, llm)

    with pytest.raises(RuntimeError, match="exceeded"):
        asyncio.run(run())
