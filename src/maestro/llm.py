"""Call Claude's messages API (or replay scripted replies from llm_mock_responses).

default_llm_factory()            # local replay, no API key
default_llm_factory(live=True)   # needs ANTHROPIC_API_KEY
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from anthropic import Anthropic

from maestro.llm_mock_responses import (
    DEFAULT_RESEARCHER_REPLIES,
    ModelMessage,
    replay,
)

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

CreateMessageFn = Callable[..., ModelMessage]


class LlmClient:
    """Thin wrapper around client.messages.create."""

    def __init__(self, create_message: CreateMessageFn) -> None:
        self._create_message = create_message

    def create_message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        return self._create_message(system=system, messages=messages, tools=tools)


LlmFactory = Callable[[bool], LlmClient]


def _anthropic_create_message(*, api_key: str, model: str) -> CreateMessageFn:
    client = Anthropic(api_key=api_key)

    def create_message(
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=messages,
            tools=tools,
        )
        return ModelMessage(
            stop_reason=response.stop_reason,
            content=tuple(block.model_dump() for block in response.content),
        )

    return create_message


def default_llm_factory(live: bool = False) -> LlmClient:
    """Return an LlmClient — mock replay by default, Anthropic when ``live`` is True."""
    if live:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "ANTHROPIC_API_KEY is required when using --live"
            raise RuntimeError(msg)
        model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        return LlmClient(_anthropic_create_message(api_key=api_key, model=model))

    return LlmClient(replay(*DEFAULT_RESEARCHER_REPLIES))
