import asyncio
from typing import Any

import pytest

from maestro.llm import (
    FETCH_URL_TOOL,
    MOCK_FETCH_URL,
    MOCK_RESEARCH_DONE_TEXT,
    LlmClient,
    ModelMessage,
    default_llm_factory,
)


def test_from_mock_returns_scripted_tool_use() -> None:
    llm = LlmClient.from_mock()

    response = llm.create_message(
        system="You are a research assistant.",
        messages=[{"role": "user", "content": "Research this subtopic: What is MCP?"}],
        tools=[FETCH_URL_TOOL],
    )

    assert response.stop_reason == "tool_use"
    requests = response.tool_use_requests()
    assert len(requests) == 1
    assert requests[0]["name"] == "fetch_url"
    assert requests[0]["input"] == {"url": MOCK_FETCH_URL}


def test_from_mock_alternates_fetch_then_done_for_each_conversation() -> None:
    llm = LlmClient.from_mock()

    first = llm.create_message(system="s", messages=[], tools=[])
    second = llm.create_message(system="s", messages=[], tools=[])
    third = llm.create_message(system="s", messages=[], tools=[])

    assert first.stop_reason == "tool_use"
    assert second.stop_reason == "end_turn"
    assert second.text() == MOCK_RESEARCH_DONE_TEXT
    assert third.stop_reason == "tool_use"


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
        assert "Example Domain" in messages[-1]["content"][0]["content"]
        return ModelMessage(
            stop_reason="end_turn",
            content=({"type": "text", "text": "Done."},),
        )

    llm = LlmClient(create_message=recording_create_message)
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


def test_default_llm_factory_without_api_key_uses_mock() -> None:
    llm = default_llm_factory()

    response = llm.create_message(
        system="s",
        messages=[{"role": "user", "content": "Research this subtopic: What is MCP?"}],
        tools=[FETCH_URL_TOOL],
    )

    assert response.stop_reason == "tool_use"


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
                    "input": {"url": MOCK_FETCH_URL},
                },
            ),
        )

    plan = ResearchPlan(question="What is MCP?", items=(PlanItem(subtopic="What is MCP?"),))
    llm = LlmClient(create_message=never_finishes)
    mcp = MagicMock()
    mcp.fetch_url = AsyncMock(return_value="Example Domain")

    async def run() -> None:
        await research(plan, mcp, llm)

    with pytest.raises(RuntimeError, match="exceeded"):
        asyncio.run(run())
