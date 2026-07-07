"""Scripted model replies for local runs and tests.

``fetch`` and ``done`` build ``ModelMessage`` values (defined in ``llm.py``).
``default_llm_factory()`` lives here because it wires ``LlmClient`` to the default
mock script; keeping it here means ``llm.py`` never has to import this module.
"""

from __future__ import annotations

from maestro.llm import LlmClient, ModelMessage

# URL the mock model puts in its fetch_url tool request.
EXAMPLE_URL = "https://example.com/"

# Text the mock model returns on its end_turn reply after a fetch.
RESEARCH_ANSWER = (
    "Example.com is a reserved domain for documentation. "
    "I fetched the page and have enough context to stop."
)


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
DEFAULT_RESEARCHER_REPLIES = (
    fetch(EXAMPLE_URL, tool_id="toolu_0"),
    done(RESEARCH_ANSWER),
)


def default_llm_factory(live: bool = False) -> LlmClient:
    """Return an LlmClient — mock replies by default, Anthropic when ``live`` is True.

    The default replies are always supplied so ``live`` runs still have something to
    fall back on if no ANTHROPIC_API_KEY is set.
    """
    return LlmClient(live=live, replies=DEFAULT_RESEARCHER_REPLIES)
