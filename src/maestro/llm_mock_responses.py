"""Scripted model replies for local runs and tests.

``fetch`` and ``done`` build ``ModelMessage`` values in the same shape the Anthropic
SDK returns. Pass them to ``replay()`` to script what the model returns each turn.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import cycle
from typing import Any

# URL the mock model puts in its fetch_url tool request.
EXAMPLE_URL = "https://example.com/"

# Text the mock model returns on its end_turn reply after a fetch.
RESEARCH_ANSWER = (
    "Example.com is a reserved domain for documentation. "
    "I fetched the page and have enough context to stop."
)


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


def fetch(url: str, *, tool_id: str) -> ModelMessage:
    """Model asks to call fetch_url."""
    return ModelMessage(
        stop_reason="tool_use",
        content=(
            {
                "type": "tool_use",
                "id": tool_id,
                "name": "fetch_url",
                "input": {"url": url},
            },
        ),
    )


def done(text: str) -> ModelMessage:
    """Model finishes with a text answer (end_turn)."""
    return ModelMessage(
        stop_reason="end_turn",
        content=({"type": "text", "text": text},),
    )


# Default script for Researcher: one fetch_url request, then one end_turn answer.
# Cycles for each plan item (fetch → done → fetch → done → …).
DEFAULT_RESEARCHER_REPLIES = (
    fetch(EXAMPLE_URL, tool_id="toolu_0"),
    done(RESEARCH_ANSWER),
)


def replay(*script: ModelMessage) -> Callable[..., ModelMessage]:
    """Return a create_message function that plays ``script`` in order, cycling."""
    responses = cycle(script)

    def create_message(
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        _ = system, messages, tools
        return next(responses)

    return create_message
