import logging
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pymongo.errors import PyMongoError

from app.shared.audit_log import AuditRecord
from app.shared.audit_log.settings import MongoSettings
from app.sys_audit.repository import MongoAuditRepository


@pytest.fixture()
def entry() -> AuditRecord:
    """Provide a minimal AuditRecord for tests."""
    return AuditRecord(
        actor_id=uuid.uuid4(),
        operation="create",
        action="catalog.product_created",
        aggregate_type="product",
        aggregate_id=uuid.uuid4(),
        trace_id="abc",
        domain="catalog",
        changes=None,
    )


@pytest.fixture()
def repo() -> MongoAuditRepository:
    """Provide a MongoAuditRepository with a patched MongoClient."""
    settings = MongoSettings(
        mongo_username="u",
        mongo_password="p",
        mongo_host="localhost",
        mongo_port=27017,
        mongo_database="audit",
    )
    with patch("app.sys_audit.repository.MongoClient") as mock_client:
        fake_collection = MagicMock()
        mock_client.return_value.__getitem__.return_value.__getitem__.return_value = (
            fake_collection
        )
        instance = MongoAuditRepository(settings)
        instance._collection = fake_collection
    return instance


class TestMongoAuditRepository:
    def test_record_inserts_serialized_document(
        self, repo: MongoAuditRepository, entry: AuditRecord
    ) -> None:
        repo.record(entry)

        repo._collection.insert_one.assert_called_once_with(
            entry.model_dump(mode="json")
        )

    def test_record_swallows_pymongo_error_and_logs_warning(
        self,
        repo: MongoAuditRepository,
        entry: AuditRecord,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        repo._collection.insert_one.side_effect = PyMongoError("connection refused")

        with caplog.at_level(logging.WARNING, logger="app.sys_audit.repository"):
            repo.record(entry)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING
