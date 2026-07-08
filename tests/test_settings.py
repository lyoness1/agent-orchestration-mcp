from pathlib import Path

from maestro import settings


def test_load_settings_applies_defaults_when_env_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "_PROJECT_ROOT", tmp_path)

    loaded = settings.load_settings()

    assert loaded.ANTHROPIC_API_KEY is None


def test_load_settings_uses_dotenv_over_defaults(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.setattr(settings, "_PROJECT_ROOT", tmp_path)

    loaded = settings.load_settings()

    assert loaded.ANTHROPIC_API_KEY == "from-dotenv"
