import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FieldChange(BaseModel):
    """Before and after values for a single changed field."""

    before: Any
    after: Any


class AuditRecord(BaseModel):
    """Immutable record of a single state-changing operation.

    Produced by domain services and written to the audit store by the
    AuditPort implementation. Once written, records must never be modified
    or removed (ADR-013).

    Fields:
        event_id: Unique identifier for this audit record.
        occurred_at: UTC timestamp of when the operation was performed.
        actor_id: UUID of the customer who performed the operation.
        operation: Coarse operation category — create, update, or delete.
        action: Fine-grained action name in <domain>.<entity>_<verb> format.
        aggregate_type: The domain entity this record is about.
        aggregate_id: UUID of the affected aggregate instance.
        trace_id: OTel trace id for cross-service correlation (ADR-005).
        domain: Name of the domain that produced this record.
        changes: Per-field before/after values. Null for delete operations.
    """

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_id: uuid.UUID
    operation: Literal["create", "update", "delete"]
    action: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    trace_id: str
    domain: str
    changes: dict[str, FieldChange] | None
