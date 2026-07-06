import asyncio
from typing import Any

import pytest

from maestro.llm import FETCH_URL_TOOL, LlmClient, ModelMessage, default_llm_factory
from maestro.llm_mock_responses import EXAMPLE_URL, RESEARCH_ANSWER


def test_default_llm_factory_first_call_requests_fetch() -> None:
    llm = default_llm_factory()

    first = llm.create_message(
        system="You are a research assistant.",
        messages=[{"role": "user", "content": "Research this subtopic: What is MCP?"}],
        tools=[FETCH_URL_TOOL],
    )

    assert first.stop_reason == "tool_use"
    assert first.tool_use_requests()[0]["input"]["url"] == EXAMPLE_URL


def test_default_llm_factory_second_call_returns_end_turn() -> None:
    llm = default_llm_factory()
    llm.create_message(system="s", messages=[], tools=[])

    second = llm.create_message(system="s", messages=[], tools=[])

    assert second.stop_reason == "end_turn"
    assert second.text() == RESEARCH_ANSWER


def test_default_llm_factory_repeats_fetch_done_for_each_subtopic() -> None:
    llm = default_llm_factory()
    for _ in range(2):
        fetch_turn = llm.create_message(system="s", messages=[], tools=[])
        done_turn = llm.create_message(system="s", messages=[], tools=[])
        assert fetch_turn.stop_reason == "tool_use"
        assert done_turn.stop_reason == "end_turn"


def test_tool_loop_appends_tool_result_to_messages() -> None:
    """Shows what gets sent on the second create_message call."""
    tool_calls: list[str] = []

    def recording_create_message(
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        if len(messages) == 1:
            tool_calls.append("first_call")
            return ModelMessage(
                stop_reason="tool_use",
                content=(
                    {
                        "type": "tool_use",
                        "id": "toolu_test_01",
                        "name": "fetch_url",
                        "input": {"url": "https://example.com/docs"},
                    },
                ),
            )
        tool_calls.append("second_call")
        assert messages[-1]["content"][0]["type"] == "tool_result"
        return ModelMessage(
            stop_reason="end_turn",
            content=({"type": "text", "text": "Done."},),
        )

    llm = LlmClient(recording_create_message)
    messages = [{"role": "user", "content": "Research this subtopic: What is MCP?"}]
    first = llm.create_message(system="s", messages=messages, tools=[FETCH_URL_TOOL])
    messages.append({"role": "assistant", "content": list(first.content)})
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_test_01",
                    "content": "Example Domain is for documentation examples.",
                }
            ],
        }
    )
    second = llm.create_message(system="s", messages=messages, tools=[FETCH_URL_TOOL])

    assert tool_calls == ["first_call", "second_call"]
    assert second.stop_reason == "end_turn"


def test_researcher_loop_raises_after_max_turns() -> None:
    from unittest.mock import AsyncMock, MagicMock

    from maestro.agents.researcher import research
    from maestro.models import PlanItem, ResearchPlan

    def never_finishes(
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        return ModelMessage(
            stop_reason="tool_use",
            content=(
                {
                    "type": "tool_use",
                    "id": "toolu_loop",
                    "name": "fetch_url",
                    "input": {"url": EXAMPLE_URL},
                },
            ),
        )

    plan = ResearchPlan(question="What is MCP?", items=(PlanItem(subtopic="What is MCP?"),))
    llm = LlmClient(never_finishes)
    mcp = MagicMock()
    mcp.fetch_url = AsyncMock(return_value="Example Domain")

    async def run() -> None:
        await research(plan, mcp, llm)

    with pytest.raises(RuntimeError, match="exceeded"):
        asyncio.run(run())
