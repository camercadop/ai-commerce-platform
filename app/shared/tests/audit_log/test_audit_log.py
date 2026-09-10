import uuid

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.shared.audit_log import (
    AuditPort,
    AuditRecord,
    FieldChange,
    NoOpAuditRepository,
    record_audit,
)
from app.shared.observability import current_trace_id


class CapturingAuditRepository(AuditPort):
    """AuditPort implementation that captures records for assertion."""

    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, entry: AuditRecord) -> None:
        """Capture the audit record."""
        self.recorded.append(entry)


@pytest.fixture()
def actor_id() -> uuid.UUID:
    """Provide a fixed actor UUID for tests."""
    return uuid.uuid4()


@pytest.fixture()
def aggregate_id() -> uuid.UUID:
    """Provide a fixed aggregate UUID for tests."""
    return uuid.uuid4()


class TestAuditRecord:
    def test_generates_event_id(self, actor_id: uuid.UUID, aggregate_id: uuid.UUID) -> None:
        record = AuditRecord(
            actor_id=actor_id,
            operation="create",
            action="catalog.product_created",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            trace_id="abc",
            domain="catalog",
            changes=None,
        )

        assert isinstance(record.event_id, uuid.UUID)

    def test_generates_occurred_at(self, actor_id: uuid.UUID, aggregate_id: uuid.UUID) -> None:
        record = AuditRecord(
            actor_id=actor_id,
            operation="create",
            action="catalog.product_created",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            trace_id="abc",
            domain="catalog",
            changes=None,
        )

        assert record.occurred_at is not None

    def test_stores_changes(self, actor_id: uuid.UUID, aggregate_id: uuid.UUID) -> None:
        changes = {"name": FieldChange(before=None, after="Widget")}
        record = AuditRecord(
            actor_id=actor_id,
            operation="create",
            action="catalog.product_created",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            trace_id="abc",
            domain="catalog",
            changes=changes,
        )

        assert record.changes is not None
        assert record.changes["name"].before is None
        assert record.changes["name"].after == "Widget"

    def test_delete_operation_has_null_changes(
        self, actor_id: uuid.UUID, aggregate_id: uuid.UUID
    ) -> None:
        record = AuditRecord(
            actor_id=actor_id,
            operation="delete",
            action="catalog.product_deleted",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            trace_id="abc",
            domain="catalog",
            changes=None,
        )

        assert record.changes is None


class TestNoOpAuditRepository:
    def test_record_does_not_raise(self, actor_id: uuid.UUID, aggregate_id: uuid.UUID) -> None:
        repo = NoOpAuditRepository()
        entry = AuditRecord(
            actor_id=actor_id,
            operation="delete",
            action="catalog.product_deleted",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            trace_id="",
            domain="catalog",
            changes=None,
        )

        repo.record(entry)


class TestRecordAudit:
    def test_writes_record_to_port(
        self, actor_id: uuid.UUID, aggregate_id: uuid.UUID
    ) -> None:
        audit = CapturingAuditRepository()

        record_audit(
            audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.product_updated",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            domain="catalog",
            changes={"name": FieldChange(before="Old", after="New")},
        )

        assert len(audit.recorded) == 1
        entry = audit.recorded[0]
        assert entry.actor_id == actor_id
        assert entry.operation == "update"
        assert entry.action == "catalog.product_updated"
        assert entry.aggregate_id == aggregate_id
        assert entry.domain == "catalog"

    def test_captures_changes(
        self, actor_id: uuid.UUID, aggregate_id: uuid.UUID
    ) -> None:
        audit = CapturingAuditRepository()

        record_audit(
            audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.product_updated",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            domain="catalog",
            changes={"name": FieldChange(before="Old", after="New")},
        )

        assert audit.recorded[0].changes is not None
        assert audit.recorded[0].changes["name"].before == "Old"
        assert audit.recorded[0].changes["name"].after == "New"

    def test_sets_trace_id_from_active_span(
        self, actor_id: uuid.UUID, aggregate_id: uuid.UUID
    ) -> None:
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        tracer = provider.get_tracer("test")
        audit = CapturingAuditRepository()

        with tracer.start_as_current_span("test-span"):
            record_audit(
                audit,
                actor_id=actor_id,
                operation="create",
                action="catalog.product_created",
                aggregate_type="product",
                aggregate_id=aggregate_id,
                domain="catalog",
                changes=None,
            )

        assert len(audit.recorded[0].trace_id) == 32

    def test_sets_empty_trace_id_when_no_active_span(
        self, actor_id: uuid.UUID, aggregate_id: uuid.UUID
    ) -> None:
        audit = CapturingAuditRepository()

        record_audit(
            audit,
            actor_id=actor_id,
            operation="create",
            action="catalog.product_created",
            aggregate_type="product",
            aggregate_id=aggregate_id,
            domain="catalog",
            changes=None,
        )

        assert audit.recorded[0].trace_id == ""


class TestCurrentTraceId:
    def test_returns_empty_string_outside_span(self) -> None:
        assert current_trace_id() == ""

    def test_returns_hex_string_inside_span(self) -> None:
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        tracer = provider.get_tracer("test")

        with tracer.start_as_current_span("test-span"):
            result = current_trace_id()

        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)
