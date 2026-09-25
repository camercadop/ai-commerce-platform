import pytest

from app.shared.audit_log import NoOpAuditRepository
from app.sys_audit.factory import resolve_audit_repo
from app.sys_audit.repository import MongoAuditRepository

_MONGO_ENV = {
    "MONGO_USERNAME": "user",
    "MONGO_PASSWORD": "pass",
    "MONGO_HOST": "localhost",
    "MONGO_PORT": "27017",
    "MONGO_DATABASE": "audit",
}


# ---------------------------------------------------------------------------
# resolve_audit_repo
# ---------------------------------------------------------------------------


class TestResolveAuditRepo:
    def test_returns_mongo_repo_when_all_vars_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key, value in _MONGO_ENV.items():
            monkeypatch.setenv(key, value)

        result = resolve_audit_repo()

        assert isinstance(result, MongoAuditRepository)

    def test_returns_noop_repo_when_all_vars_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key in _MONGO_ENV:
            monkeypatch.delenv(key, raising=False)

        result = resolve_audit_repo()

        assert isinstance(result, NoOpAuditRepository)

    def test_returns_noop_repo_when_any_var_missing(
        self, monkeypatch: pytest.MonkeyPatch, subtests: pytest.Subtests
    ) -> None:
        for missing_key in _MONGO_ENV:
            with subtests.test(missing_key):
                for key, value in _MONGO_ENV.items():
                    monkeypatch.setenv(key, value)
                monkeypatch.delenv(missing_key)

                result = resolve_audit_repo()

                assert isinstance(result, NoOpAuditRepository)
