import uuid
from typing import Literal

from app.shared.audit_log.port import AuditPort
from app.shared.audit_log.schemas import AuditRecord, FieldChange
from app.shared.observability import current_trace_id


def record_audit(
    audit: AuditPort,
    *,
    actor_id: uuid.UUID,
    operation: Literal["create", "update", "delete"],
    action: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    domain: str,
    changes: dict[str, FieldChange] | None,
) -> None:
    """Build and write an audit record via the given port.

    Captures the active trace ID automatically. Delegates failure handling
    to the AuditPort implementation — callers are never notified of write
    failures (ADR-013).

    Args:
        audit: The audit port to write to.
        actor_id: UUID of the customer who performed the operation.
        operation: Coarse operation category — create, update, or delete.
        action: Fine-grained action name in <domain>.<entity>_<verb> format.
        aggregate_type: The domain entity this record is about.
        aggregate_id: UUID of the affected aggregate instance.
        domain: Name of the domain producing this record.
        changes: Per-field before/after values. None for delete operations.
    """
    audit.record(
        AuditRecord(
            actor_id=actor_id,
            operation=operation,
            action=action,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            trace_id=current_trace_id(),
            domain=domain,
            changes=changes,
        )
    )
