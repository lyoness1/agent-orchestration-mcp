"""Anthropic-backed LLM client and the tool-use loop shared by agents.

This module owns the conversation with the Anthropic API: it sends messages,
runs the tool-use loop, and asks a caller-supplied executor to run any tool the
model requests. It knows nothing about which tools exist or how they run, so the
same loop works for any agent that supplies tool schemas and an executor.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message, ToolParam

API_KEY_ENV = "ANTHROPIC_API_KEY"

# Alias tracks the latest Sonnet; override per call if a run needs a different model.
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 4096

# Cap on model turns in the tool loop. Without a bound a confused model can call
# tools forever, burning tokens and wall-clock time; see DESIGN.md operational
# constraints. When the budget runs out we force one final tool-free answer.
DEFAULT_MAX_TURNS = 8

_FORCE_ANSWER = (
    "You have reached the research budget. Stop calling tools and answer the "
    "question now using the evidence you have already gathered."
)

# Callback that runs a tool the model asked for and returns its text output.
ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]


class MissingApiKeyError(RuntimeError):
    """Raised when the Anthropic API key is not present in the environment."""

    def __init__(self) -> None:
        super().__init__(f"{API_KEY_ENV} is not set. Export a valid Anthropic API key and re-run.")


def _text_from_message(message: Message) -> str:
    """Join the text blocks of an assistant message into a single string."""
    parts = [block.text for block in message.content if block.type == "text"]
    return "\n".join(parts).strip()


class LlmClient:
    """Thin async wrapper over the Anthropic Messages API with a tool loop."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_turns: int = DEFAULT_MAX_TURNS,
    ) -> None:
        # Fail before any network call if the key is missing, so callers get a
        # clear error instead of an opaque auth failure mid-run.
        if not os.environ.get(API_KEY_ENV):
            raise MissingApiKeyError
        self._client = AsyncAnthropic()
        self._model = model
        self._max_tokens = max_tokens
        self._max_turns = max_turns

    async def run_tool_loop(
        self,
        *,
        system: str,
        prompt: str,
        tools: list[ToolParam],
        execute_tool: ToolExecutor,
    ) -> str:
        """Drive the model until it answers, running tools it requests along the way.

        Each turn: send the running transcript; if the model asks to use tools,
        run every requested tool via ``execute_tool`` and feed the results back;
        otherwise return the model's text. If the turn budget is exhausted, make
        one final tool-free request so the run always ends with an answer.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        for _ in range(self._max_turns):
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                return _text_from_message(response)

            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "tool_use":
                    output = await execute_tool(block.name, dict(block.input))
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})

        messages.append({"role": "user", "content": _FORCE_ANSWER})
        final = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=messages,
        )
        return _text_from_message(final)
