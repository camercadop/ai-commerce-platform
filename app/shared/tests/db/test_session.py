import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.shared.db import DatabaseSettings, build_session_factory, get_db


def test_database_settings_fails_on_missing_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        DatabaseSettings(_env_file=None)


def test_database_settings_loads_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    settings = DatabaseSettings()

    assert settings.database_url == "sqlite:///:memory:"


def test_build_session_factory_returns_sessions() -> None:
    factory = build_session_factory("sqlite:///:memory:")
    sessions = list(get_db(factory))

    assert len(sessions) == 1
    assert isinstance(sessions[0], Session)


def test_get_db_session_is_usable() -> None:
    factory = build_session_factory("sqlite:///:memory:")

    for session in get_db(factory):
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
