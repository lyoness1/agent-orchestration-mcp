"""Call Claude's messages API (or a local mock with the same shape).

Researcher uses create_message() in a loop: the model may request fetch_url, the app
runs MCP and sends page text back, then the model replies again. One create_message()
call equals one round trip — the same method Anthropic documents.

Without ANTHROPIC_API_KEY, default_llm_factory() uses LlmClient.from_mock() so you can
learn the flow without spending tokens.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default URL the mock model requests via fetch_url (until the model picks URLs live).
MOCK_FETCH_URL = "https://example.com/"

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Text the mock returns on the final turn (after a pretend fetch).
MOCK_RESEARCH_DONE_TEXT = (
    "MCP is an open protocol that connects AI applications to external systems. "
    "I read the fetched introduction page and have enough context to stop."
)

# Anthropic tools= argument shape for fetch_url (LLM-facing; MCP bridge may own this later).
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

# ---------------------------------------------------------------------------
# SDK-shaped types (used only in this module — not pipeline agent artifacts)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelMessage:
    """One client.messages.create() response — what Researcher reads each turn."""

    stop_reason: str
    content: tuple[dict[str, Any], ...]

    def text(self) -> str:
        """Assistant prose from this turn (empty if the model only requested tools)."""
        parts = [block["text"] for block in self.content if block.get("type") == "text"]
        return "\n".join(parts)

    def tool_use_requests(self) -> tuple[dict[str, Any], ...]:
        """Tool calls the model wants us to run (e.g. fetch_url)."""
        return tuple(block for block in self.content if block.get("type") == "tool_use")


# Must follow ModelMessage: unlike function annotations, this alias is evaluated now.
CreateMessageFn = Callable[..., ModelMessage]

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LlmClient:
    """Thin wrapper around client.messages.create for tests and agents."""

    def __init__(self, create_message: CreateMessageFn) -> None:
        self._create_message = create_message

    def create_message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        """One API round trip: conversation so far in, model reply out."""
        return self._create_message(system=system, messages=messages, tools=tools)

    @staticmethod
    def from_mock(*, fetch_url: str = MOCK_FETCH_URL) -> LlmClient:
        """Local scripted model: fetch once, then return MOCK_RESEARCH_DONE_TEXT."""
        return LlmClient(create_message=_build_mock_create_message(fetch_url=fetch_url))

    @staticmethod
    def from_anthropic(*, api_key: str, model: str = DEFAULT_MODEL) -> LlmClient:
        """Real Anthropic SDK — used when ANTHROPIC_API_KEY is set."""
        return LlmClient(
            create_message=_build_anthropic_create_message(api_key=api_key, model=model),
        )


LlmFactory = Callable[[], LlmClient]

# ---------------------------------------------------------------------------
# Backends (implementation for from_mock / from_anthropic; replaced by fixtures in 3c)
# ---------------------------------------------------------------------------


def _build_mock_create_message(*, fetch_url: str) -> CreateMessageFn:
    """Return a create_message function that scripts fetch → done without API calls."""
    api_call_count = 0

    def create_message(
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelMessage:
        nonlocal api_call_count
        _ = system, messages, tools
        api_call_count += 1
        if api_call_count % 2 == 1:
            return ModelMessage(
                stop_reason="tool_use",
                content=(
                    {
                        "type": "tool_use",
                        "id": f"toolu_mock_{api_call_count:02d}",
                        "name": "fetch_url",
                        "input": {"url": fetch_url},
                    },
                ),
            )
        return ModelMessage(
            stop_reason="end_turn",
            content=({"type": "text", "text": MOCK_RESEARCH_DONE_TEXT},),
        )

    return create_message


def _build_anthropic_create_message(*, api_key: str, model: str) -> CreateMessageFn:
    """Return a create_message function that calls the Anthropic SDK."""

    from anthropic import Anthropic

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


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_llm_factory() -> LlmClient:
    """Return an LlmClient: Anthropic when ANTHROPIC_API_KEY is set, else mock."""
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        return LlmClient.from_anthropic(api_key=api_key, model=model)
    return LlmClient.from_mock()
