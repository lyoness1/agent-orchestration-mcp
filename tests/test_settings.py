from pathlib import Path

from maestro import settings
from maestro.settings import Settings


def test_load_settings_applies_defaults_when_env_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "_PROJECT_ROOT", tmp_path)

    loaded = settings.load_settings()

    assert loaded.ANTHROPIC_API_KEY is None
    assert loaded.LLM_DEFAULT_MODEL == "claude-sonnet-4-5"
    assert loaded.LLM_DEFAULT_MAX_TOKENS == 4096
    assert loaded.LLM_DEFAULT_MAX_TURNS == 8
    assert loaded.MCP_REQUEST_TIMEOUT == 10.0
    assert loaded.MCP_MAX_CHARS == 6000


def test_load_settings_uses_dotenv_over_defaults(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.setattr(settings, "_PROJECT_ROOT", tmp_path)

    loaded = settings.load_settings()

    assert loaded.ANTHROPIC_API_KEY == "from-dotenv"


def test_load_settings_coerces_numeric_dotenv_values(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "LLM_DEFAULT_MAX_TOKENS=8192\nMCP_REQUEST_TIMEOUT=5.5\nMCP_MAX_CHARS=8000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "_PROJECT_ROOT", tmp_path)

    loaded = settings.load_settings()

    assert loaded.LLM_DEFAULT_MAX_TOKENS == 8192
    assert loaded.MCP_REQUEST_TIMEOUT == 5.5
    assert loaded.MCP_MAX_CHARS == 8000


def test_module_settings_is_a_settings_instance() -> None:
    assert isinstance(settings.settings, Settings)
