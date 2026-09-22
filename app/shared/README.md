# shared

Platform infrastructure shared across all domain modules. Contains no business logic.
If a package here starts depending on domain concepts (products, orders, customers),
it belongs in a domain module instead.

## Rationale

Without a shared layer, every domain would independently implement session management,
JWT validation, response formatting, and observability setup — leading to divergent
patterns, duplicated bugs, and no consistent contract between services.

`app/shared/` solves this by centralizing platform primitives behind stable interfaces.
Domains consume these interfaces without knowing the underlying provider, which keeps
them portable and independently testable. Swapping a concrete implementation (e.g.
replacing the audit store or the message broker) requires no changes to domain code.

## Module layout

```
app/shared/
├── api/                # Response envelope, pagination, and input sanitization
├── audit_log/          # Abstract audit port, record schema, and write helper
├── auth/               # JWT validation and FastAPI auth dependency factory
├── config/             # Base settings class for environment-driven configuration
├── db/                 # ORM base, model mixins, generic repository, and session factory
├── events/             # Abstract message broker port and event envelope
├── observability/      # Structured logging and OpenTelemetry tracing
├── storage/            # Abstract object storage port
└── exceptions.py       # Shared base exception classes
```

## Design rules

### Port/adapter boundary

`audit_log/`, `events/`, and `storage/` expose abstract ports only. Concrete
implementations live in the domain modules that require them (e.g. `app/sys_audit/`).
Domain code must depend on the port, never on a concrete implementation (ADR-004).

### No cross-domain imports

No package in `app/shared/` may import from any domain module (`app/catalog/`,
`app/identity/`, etc.). The dependency arrow always points inward: domains depend
on shared, never the other way around.

### Startup validation

All settings subclass `AppSettings` from `config/`. Missing or invalid configuration
values raise a `ValidationError` at startup, before the application serves any
traffic (ADR-015).

## Usage

### Configuration

Every domain subclasses `AppSettings` and declares its own configuration keys:

```python
from app.shared.config import AppSettings


class CatalogSettings(AppSettings):
    database_base_url: str
    kafka_bootstrap_servers: str
```

### Database session

Build the session factory once at startup, then produce a FastAPI dependency with
`make_get_db`:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.shared.db import build_session_factory, make_get_db

session_factory = build_session_factory(settings.database_base_url)
DbDep = Annotated[Session, Depends(make_get_db(session_factory))]
```

Domain models inherit `BaseModel` and the relevant mixins:

```python
from app.shared.db import BaseModel, SoftDeleteMixin, TimestampMixin


class Product(BaseModel, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

Domain repositories subclass `BaseRepository`:

```python
from app.shared.db import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model_class = Product
```

### Auth

Build the dependency once at startup and inject it into protected routes:

```python
from typing import Annotated
from fastapi import Depends
from app.shared.auth import JWTValidator, TokenClaims, build_auth_dependency

validator = JWTValidator(public_key=settings.auth_jwt_public_key)
get_current_user = build_auth_dependency(validator)
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


@router.get("/orders")
def list_orders(claims: CurrentUser) -> list[OrderResponse]:
    actor_id = claims.actor_id()
    ...
```

### Response envelope

All API responses must use the platform envelope:

```python
from app.shared.api import DataResponse, PaginatedResponse, error_response

return DataResponse(data=product)
return JSONResponse(status_code=404, content=error_response("PRODUCT_NOT_FOUND", "..."))
```

### Observability

Call both setup functions once at application startup:

```python
from app.shared.observability import configure_logging, configure_tracing

configure_logging()
configure_tracing(
    service_name=settings.otel_service_name,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    enabled=settings.otel_enabled,
)
```

Use `current_trace_id()` to propagate trace context into events and audit records:

```python
from app.shared.observability import current_trace_id

trace_id = current_trace_id()  # 32-char hex string, or "" if no active span
```

### Events

Publish domain events through the `MessageBroker` port using `EventEnvelope`:

```python
from app.shared.events import EventEnvelope, MessageBroker
from app.shared.observability import current_trace_id

broker.publish(
    "catalog.product.created",
    EventEnvelope(
        event_type="ProductCreated",
        version=1,
        producer="catalog",
        aggregate_type="product",
        aggregate_id=str(product.id),
        trace_id=current_trace_id(),
        data={"id": str(product.id), "name": product.name},
    ),
)
```

### Audit log

Depend on `AuditPort` and call `record_audit()` — never import from `app/sys_audit/`
directly:

```python
from app.shared.audit_log import AuditPort, FieldChange, record_audit

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
```

### Exceptions

Domain exceptions extend the shared base classes so callers can catch by category:

```python
from app.shared.exceptions import ResourceAlreadyExists, ResourceNotFound


class ProductNotFound(ResourceNotFound):
    code = "PRODUCT_NOT_FOUND"
    resource_name = "Product"


class ProductAlreadyExists(ResourceAlreadyExists):
    code = "PRODUCT_ALREADY_EXISTS"
    resource_name = "Product"
```

| Class | Default code | Use |
| --- | --- | --- |
| `ResourceNotFound` | `NOT_FOUND` | Resource does not exist or was soft-deleted |
| `ResourceAlreadyExists` | `ALREADY_EXISTS` | Uniqueness constraint violation |

## Dependency injection

Each domain owns a `DeclarativeContainer` that holds infrastructure singletons —
`audit` and `broker` — shared across all requests. Request-scoped objects (db
session, services) stay under FastAPI's control.

In `routes.py`, declare sentinel dependencies:

```python
from app.shared.audit_log import AuditPort
from app.shared.events import MessageBroker


def _audit_dependency() -> AuditPort: ...
def _broker_dependency() -> MessageBroker: ...


AuditDep = Annotated[AuditPort, Depends(_audit_dependency)]
BrokerDep = Annotated[MessageBroker, Depends(_broker_dependency)]
```

In `container.py`, declare the singletons:

```python
from dependency_injector import containers, providers
from app.shared.audit_log import AuditPort, NoOpAuditRepository
from app.shared.events import MessageBroker, NoOpMessageBroker


class CatalogContainer(containers.DeclarativeContainer):
    audit: providers.Singleton[AuditPort] = providers.Singleton(NoOpAuditRepository)
    broker: providers.Singleton[MessageBroker] = providers.Singleton(NoOpMessageBroker)
```

In `app.py`, override the sentinels and wire the container at startup:

```python
container = CatalogContainer()
container.audit.override(MongoAuditRepository(mongo_settings))
container.broker.override(resolved_broker)
app.state.container = container

app.dependency_overrides[_audit_dependency] = lambda: container.audit()
app.dependency_overrides[_broker_dependency] = lambda: container.broker()
```

In tests, override with no-ops:

```python
container = CatalogContainer()
container.audit.override(NoOpAuditRepository())
container.broker.override(NoOpMessageBroker())
```
