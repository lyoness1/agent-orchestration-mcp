"""Call Claude's messages API, or replay a canned list of mock replies.

default_llm_factory()      # mock replies, no API key (see llm_mock_responses)
LlmClient(live=True, ...)   # real Anthropic calls; falls back to mock without a key
LlmClient(replies=...)      # replay a specific list of ModelMessage replies
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from itertools import cycle
from typing import Any

from anthropic import Anthropic

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Passed to client.messages.create(..., tools=[...]) on every call.
FETCH_URL_TOOL: dict[str, Any] = {
    "name": "fetch_url",
    "description": "Fetch a web page and return its text content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "HTTP or HTTPS URL to fetch"},
        },
        "required": ["url"],
    },
}


@dataclass(frozen=True)
class ModelMessage:
    """One client.messages.create() response — what agents read each turn."""

    stop_reason: str
    content: tuple[dict[str, Any], ...]

    def text(self) -> str:
        parts = [block["text"] for block in self.content if block.get("type") == "text"]
        return "\n".join(parts)

    def tool_use_requests(self) -> tuple[dict[str, Any], ...]:
        return tuple(block for block in self.content if block.get("type") == "tool_use")


@dataclass(frozen=True)
class _MockBlock:
    """A content block that quacks like an Anthropic SDK block (has model_dump)."""

    data: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return self.data


@dataclass(frozen=True)
class _MockResponse:
    """A messages.create() return value that quacks like an Anthropic response."""

    stop_reason: str
    content: list[_MockBlock]


class _MockMessages:
    """The ``.messages`` namespace of MockAnthropic; exposes create() like the SDK."""

    def __init__(self, script: tuple[ModelMessage, ...]) -> None:
        self._script = cycle(script)
        self._tool_use_count = 0

    def create(self, *, model: str, max_tokens: int, system: str, messages: list, tools: list):
        _ = model, max_tokens, system, messages, tools
        message = next(self._script)
        blocks = list(message.content)
        if message.stop_reason == "tool_use":
            self._tool_use_count += 1
            blocks = [{**blocks[0], "id": f"toolu_{self._tool_use_count}"}]
        return _MockResponse(
            stop_reason=message.stop_reason,
            content=[_MockBlock(block) for block in blocks],
        )


class MockAnthropic:
    """Drop-in for ``anthropic.Anthropic`` that replays a scripted list of replies.

    The script cycles, so multiple plan items each get fetch -> done. Tool-use ids
    are renumbered (toolu_1, toolu_2, ...) to mimic the unique ids the real API
    returns. The conversation (system/messages/tools) is ignored — the mock does
    not "read" like a real model; a future multi-agent mock could route on the
    system prompt instead.
    """

    def __init__(self, script: tuple[ModelMessage, ...]) -> None:
        self.messages = _MockMessages(script)


class LlmClient:
    """One entry point for LLM turns; mock by default, Anthropic when ``live``."""

    def __init__(self, *, replies: tuple[ModelMessage, ...], live: bool = False) -> None:
        self._model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if live and api_key:
            self._client: Anthropic | MockAnthropic = Anthropic(api_key=api_key)
        else:
            if live:
                print(
                    "ANTHROPIC_API_KEY is not set — replaying mock responses instead.",
                    file=sys.stderr,
                )
            self._client = MockAnthropic(replies)

    def create_message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        """One round trip: conversation so far in, model reply out."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=messages,
            tools=tools,
        )
        return ModelMessage(
            stop_reason=response.stop_reason,
            content=tuple(block.model_dump() for block in response.content),
        )


LlmFactory = Callable[[bool], LlmClient]
