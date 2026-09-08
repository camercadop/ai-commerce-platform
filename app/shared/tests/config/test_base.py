import pytest
from pydantic import ValidationError

from app.shared.config import AppSettings


class DatabaseSettings(AppSettings):
    """Example domain settings used in tests."""

    db_host: str
    db_port: int
    db_name: str


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "commerce")

    settings = DatabaseSettings()

    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert settings.db_name == "commerce"


def test_settings_fails_on_missing_required_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)

    with pytest.raises(ValidationError):
        DatabaseSettings()


def test_settings_fails_on_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "not-a-number")
    monkeypatch.setenv("DB_NAME", "commerce")

    with pytest.raises(ValidationError):
        DatabaseSettings()


def test_settings_ignores_extra_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "commerce")
    monkeypatch.setenv("UNKNOWN_KEY", "should-be-ignored")

    settings = DatabaseSettings()

    assert not hasattr(settings, "unknown_key")
