"""Application settings loaded from defaults + `.env`.

``settings`` is built once when this module is first imported (typically at process
startup).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import dotenv_values

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Application settings: dataclass defaults with optional `.env` overrides."""

    # Secret — required for live Anthropic calls.
    ANTHROPIC_API_KEY: str | None = None

    # Alias tracks the latest Sonnet; override per ``LlmClient`` call if needed.
    LLM_DEFAULT_MODEL: str = "claude-sonnet-4-5"
    LLM_DEFAULT_MAX_TOKENS: int = 4096
    # Cap on model turns in the tool loop. Without a bound a confused model can call
    # tools forever, burning tokens and wall-clock time; see DESIGN.md operational
    # constraints. When the budget runs out we force one final tool-free answer.
    LLM_DEFAULT_MAX_TURNS: int = 8

    # Fail fast on slow hosts; agents can retry or pick another source.
    MCP_REQUEST_TIMEOUT: float = 10.0
    # Cap tool output before it re-enters the LLM context. Tokens are rough (~4
    # ASCII chars per token for English; model and content vary). Uncapped pages
    # blow the context window and add cost/latency. Tune by task: quick skim 4k-8k,
    # deeper read 10k-20k; above ~20k use chunking (multiple fetches or ingest)
    # instead of one blob.
    MCP_MAX_CHARS: int = 6000


def load_settings() -> Settings:
    """Build settings from defaults, with `.env` values overriding."""
    values = asdict(Settings())
    file_values = dotenv_values(_PROJECT_ROOT / ".env")
    for key in values:
        file_value = file_values.get(key)
        if file_value is None:
            continue
        default_value = values[key]
        if isinstance(default_value, int):
            values[key] = int(file_value)
        elif isinstance(default_value, float):
            values[key] = float(file_value)
        else:
            values[key] = file_value
    return Settings(**values)


settings = load_settings()
