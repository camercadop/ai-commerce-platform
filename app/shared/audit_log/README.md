# audit_log

Defines the abstract audit port and the supporting types domain services use to record
state-changing operations. Concrete store implementations live outside `app/shared/`
(e.g. `app/sys_audit/`). Domain code must never import a concrete implementation
directly (ADR-004, ADR-013).

## Package layout

```
audit_log/
├── __init__.py     # Package entry point
├── port.py         # Audit abstraction layer
├── repository.py   # No-op audit implementation for tests and dev
├── schemas.py      # Audit record value objects
├── settings.py     # Audit store configuration
└── utils.py        # Audit write helper
```

## Public API

| Symbol | Description |
| --- | --- |
| `AuditPort` | Abstract base class all audit implementations must satisfy |
| `AuditRecord` | Immutable value object representing a single audited operation |
| `FieldChange` | Before/after pair for a single changed field |
| `record_audit(audit, *, ...)` | Builds an `AuditRecord` and writes it via the given port |
| `NoOpAuditRepository` | No-op implementation that discards all records — use in tests and dev |
| `MongoSettings` | `AppSettings` subclass for the MongoDB audit store connection |

### record_audit() parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `audit` | `AuditPort` | The port instance to write to |
| `actor_id` | `UUID` | Customer who performed the operation |
| `operation` | `create \| update \| delete` | Coarse operation category |
| `action` | `str` | Fine-grained name in `<domain>.<entity>_<verb>` format |
| `aggregate_type` | `str` | Domain entity this record is about |
| `aggregate_id` | `UUID` | Affected aggregate instance |
| `domain` | `str` | Domain producing this record |
| `changes` | `dict[str, FieldChange] \| None` | Per-field before/after values; `None` for deletes |

`record_audit()` captures the active OTel trace ID automatically via `current_trace_id()`.

```python
from app.shared.audit_log import AuditPort, FieldChange, record_audit


def update(
    self, product_id: uuid.UUID, actor_id: uuid.UUID, data: dict[str, Any]
) -> Product:
    product = self.repo.get_by_id(product_id)
    before = {k: getattr(product, k) for k in data}
    updated = self.repo.update(product, data)
    record_audit(
        self._audit,
        actor_id=actor_id,
        operation="update",
        action="catalog.product_updated",
        aggregate_type="product",
        aggregate_id=product_id,
        domain="catalog",
        changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
    )
    return updated
```

### FieldChange fields

| Field | Type | Description |
| --- | --- | --- |
| `before` | `Any` | Field value before the operation |
| `after` | `Any` | Field value after the operation |

### AuditRecord fields

| Field | Type | Description |
| --- | --- | --- |
| `event_id` | `UUID` | Unique identifier for this record |
| `occurred_at` | `datetime` | UTC timestamp of the operation |
| `actor_id` | `UUID` | Customer who performed the operation |
| `operation` | `create \| update \| delete` | Coarse operation category |
| `action` | `str` | Fine-grained name in `<domain>.<entity>_<verb>` format |
| `aggregate_type` | `str` | Domain entity this record is about |
| `aggregate_id` | `UUID` | Affected aggregate instance |
| `trace_id` | `str` | OTel trace ID for cross-service correlation |
| `domain` | `str` | Domain that produced this record |
| `changes` | `dict[str, FieldChange] \| None` | Per-field before/after values; `None` for deletes |

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `MONGO_USERNAME` | MongoDB username | required |
| `MONGO_PASSWORD` | MongoDB password | required |
| `MONGO_HOST` | MongoDB host | required |
| `MONGO_PORT` | MongoDB port | required |
| `MONGO_DATABASE` | Database name for audit records | required |

## Failure contract

Audit writes are best-effort. `AuditPort.record()` implementations must catch all
exceptions internally, log a warning, and never propagate failures to the caller.
A failed audit write must never roll back the domain transaction (ADR-013).
