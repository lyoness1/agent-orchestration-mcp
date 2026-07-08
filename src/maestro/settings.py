"""Application settings loaded from defaults + `.env`."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import dotenv_values

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Default settings values used when environment does not provide them."""

    ANTHROPIC_API_KEY: str | None = None

    LLM_DEFAULT_MODEL: str = "claude-sonnet-4-5"
    LLM_DEFAULT_MAX_TOKENS: int = 4096
    LLM_DEFAULT_MAX_TURNS: int = 8

    MCP_REQUEST_TIMEOUT: float = 10.0
    MCP_MAX_CHARS: int = 6000


def load_settings() -> Settings:
    """Build settings from defaults, with `.env` values overriding."""
    values = asdict(Settings())
    file_values = dotenv_values(_PROJECT_ROOT / ".env")
    for key in values:
        file_value = file_values.get(key)
        if file_value is not None:
            values[key] = file_value
    return Settings(**values)


settings = load_settings()
