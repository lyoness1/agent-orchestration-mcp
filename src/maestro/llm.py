"""Anthropic-backed LLM client and the tool-use loop shared by agents.

This module owns the conversation with the Anthropic API: it sends messages,
runs the tool-use loop, and asks a caller-supplied executor to run any tool the
model requests. It knows nothing about which tools exist or how they run, so the
same loop works for any agent that supplies tool schemas and an executor.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message, ToolParam

from maestro.settings import settings

_FORCE_ANSWER = (
    "You have reached the research budget. Stop calling tools and answer the "
    "question now using the evidence you have already gathered."
)

# Callback that runs a tool the model asked for and returns its text output.
ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]


class MissingApiKeyError(RuntimeError):
    """Raised when the Anthropic API key is not present in the environment."""

    def __init__(self) -> None:
        super().__init__("ANTHROPIC_API_KEY is not set.")


def _text_from_message(message: Message) -> str:
    """Join the text blocks of an assistant message into a single string."""
    parts = [block.text for block in message.content if block.type == "text"]
    return "\n".join(parts).strip()


class LlmClient:
    """Thin async wrapper over the Anthropic Messages API with a tool loop."""

    def __init__(
        self,
        *,
        model: str = settings.LLM_DEFAULT_MODEL,
        max_tokens: int = settings.LLM_DEFAULT_MAX_TOKENS,
        max_turns: int = settings.LLM_DEFAULT_MAX_TURNS,
    ) -> None:
        # Fail before any network call if the key is missing, so callers get a
        # clear error instead of an opaque auth failure mid-run.
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise MissingApiKeyError
        self._client = AsyncAnthropic(api_key=api_key)
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
