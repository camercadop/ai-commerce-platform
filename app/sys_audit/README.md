# sys_audit

Platform-level audit log implementation. Writes audit records to MongoDB.

This module contains the concrete implementation of the `AuditPort` defined in
`app/shared/audit_log/`. Domain modules must never import from here directly —
they depend only on `app/shared/audit_log/` (ADR-001, ADR-004). The concrete
repository is wired at the application level in each domain's `app.py`.

## Module layout

```
app/sys_audit/
├── repository.py   # MongoAuditRepository — writes records to MongoDB
└── __init__.py
```

## How it works

`MongoAuditRepository` receives an `AuditRecord` from the domain service via
`record_audit()` and inserts it as an immutable document into the `audit_records`
MongoDB collection. Failures are caught and logged as warnings — the domain
transaction is never rolled back due to an audit write failure (ADR-013).

## Wiring

Instantiate `MongoAuditRepository` in the domain's `app.py` and override the
`_audit_dependency` sentinel:

```python
from app.shared.audit_log import MongoSettings
from app.sys_audit import MongoAuditRepository

audit_repo = MongoAuditRepository(MongoSettings())
app.dependency_overrides[_audit_dependency] = lambda: audit_repo
```

When MongoDB is not available (tests, local development), omit `mongo_settings`
from `create_app` — a `NoOpAuditRepository` is used automatically.

## Dependencies

| Dependency | Purpose | Required |
| --- | --- | --- |
| MongoDB | Audit record store | Yes (production) |

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `MONGO_USERNAME` | MongoDB username | required |
| `MONGO_PASSWORD` | MongoDB password | required |
| `MONGO_HOST` | MongoDB host | required |
| `MONGO_PORT` | MongoDB port | required |
| `MONGO_DATABASE` | Database name for audit records | required |
