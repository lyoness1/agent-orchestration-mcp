"""Application defaults and environment bootstrap.

``load_env()`` is called from the CLI entry point before the orchestrator runs.
It merges values into ``os.environ`` with precedence:

1. Values from ``.env`` in the project root (highest — overwrites shell and defaults)
2. UPPERCASE constants defined in this module (defaults for unset keys)

Shell exports are not preserved when ``.env`` defines the same key.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ANTHROPIC_API_KEY: str | None = None

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _constant_defaults() -> dict[str, str]:
    """Return env-style defaults from this module's UPPERCASE constants."""
    defaults: dict[str, str] = {}
    for name, value in globals().items():
        if not name.isupper() or name.startswith("_"):
            continue
        if value is None:
            continue
        defaults[name] = str(value)
    return defaults


def load_env() -> None:
    """Load settings into ``os.environ``: ``.env`` overrides defaults and shell."""
    for key, value in _constant_defaults().items():
        os.environ.setdefault(key, value)

    load_dotenv(_PROJECT_ROOT / ".env", override=True)
