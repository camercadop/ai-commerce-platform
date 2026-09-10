# Shared

Platform infrastructure shared across all domain modules.

This module contains no business logic. If a package here starts depending on domain
concepts (products, orders, customers), it belongs in a domain module instead.

## Packages

| Package | Responsibility |
| --- | --- |
| `api/` | Uniform response envelope, error schemas, and shared validators (ADR-014) |
| `auth/` | Provider-agnostic JWT validation, auth middleware, token claims extraction |
| `config/` | Pydantic Settings base class, startup validation (ADR-015) |
| `db/` | SQLAlchemy engine, session factory, declarative base, generic repository |
| `events/` | Event envelope model, abstract message broker port (ADR-004) |
| `exceptions.py` | Shared base exception classes (`ResourceNotFound`, `ResourceAlreadyExists`) |
| `observability/` | OpenTelemetry tracing setup, structured logging (ADR-005) |
| `storage/` | Abstract object storage port (ADR-004) |

## Usage

### CRUD router

Use `CRUDRouter` from `shared/api/` to generate standard `POST`, `GET /{id}`,
`PATCH /{id}`, and `DELETE /{id}` routes for a flat resource without boilerplate:

```python
from app.shared.api import CRUDRouter

router = CRUDRouter(
    prefix="/api/v1/products",
    response_model=ProductResponse,
    create_schema=CreateProductRequest,
    update_schema=UpdateProductRequest,
    get_db_dep=get_db,
    service=ProductService,
)
```

Override `to_response` when custom mapping logic is needed, and individual `_fn`
arguments when the service method names differ from the convention (`create`, `get`,
`update`, `delete`):

```python
router = CRUDRouter(
    ...,
    service=ProductService,
    create_fn=lambda body, db: ProductService(db).register(**body.model_dump()),
)
```

Add custom routes directly on the returned router for non-standard operations.

### String sanitization

Use `sanitize_strings` to strip control characters from string fields across any schema.
Assign the result to `_strip` — Pydantic registers it as a validator automatically.

```python
from app.shared.api import sanitize_strings


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)

    _strip = sanitize_strings("name", "description")
```

### Response envelope

All API responses must use the platform envelope from `shared/api/`:

```python
from app.shared.api import DataResponse, PaginatedResponse, error_response

# single resource
return DataResponse(data=product)

# collection
return PaginatedResponse(
    data=products, pagination=PaginationMeta(next_cursor=cursor, has_more=True)
)

# error (in exception handlers)
return JSONResponse(status_code=404, content=error_response("PRODUCT_NOT_FOUND", "..."))
```

### Settings

Every domain subclasses `AppSettings` and declares its own configuration keys:

```python
from app.shared.config import AppSettings


class CatalogSettings(AppSettings):
    database_url: str
    kafka_bootstrap_servers: str
```

### Database session

Inject the session using the `Annotated` pattern — never use `Depends()` in default
arguments:

```python
from typing import Annotated
from app.shared.db import build_session_factory, get_db
from fastapi import Depends

session_factory = build_session_factory(settings.database_url)
DbDep = Annotated[Session, Depends(get_db)]


@router.get("/products/{id}")
def get_product(id: uuid.UUID, db: DbDep) -> ProductResponse: ...
```

Domain repositories extend `BaseRepository` for generic CRUD:

```python
from app.shared.db import BaseRepository
from app.catalog.models import Product


class ProductRepository(BaseRepository[Product]):
    model_class = Product
```

### Exceptions

Domain exceptions extend the shared base classes so callers can catch by category:

```python
from app.shared.exceptions import ResourceNotFound, ResourceAlreadyExists


class ProductNotFound(ResourceNotFound):
    code = "PRODUCT_NOT_FOUND"
    resource_name = "Product"


class ProductAlreadyExists(ResourceAlreadyExists):
    code = "PRODUCT_ALREADY_EXISTS"
    resource_name = "Product"
```

### Events

Publish events through the domain's `events.py` using the `EventEnvelope`:

```python
from app.shared.events import EventEnvelope, MessageBroker

broker.publish(
    "catalog.product.created",
    EventEnvelope(
        event_type="ProductCreated",
        version=1,
        producer="catalog",
        aggregate_type="product",
        aggregate_id=str(product.id),
        trace_id=current_trace_id(),
        data=payload.model_dump(),
    ),
)
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

### Auth

Build the dependency at startup and inject it into protected routes using `Annotated`:

```python
from typing import Annotated
from app.shared.auth import JWTValidator, build_auth_dependency, TokenClaims
from fastapi import Depends

validator = JWTValidator(public_key=settings.auth_jwt_public_key)
get_current_user = build_auth_dependency(validator)
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


@router.get("/orders")
def list_orders(claims: CurrentUser) -> list[OrderResponse]: ...
```

### Storage

Depend on the `ObjectStorage` port — never on a concrete implementation:

```python
from app.shared.storage import ObjectStorage, ObjectNotFound


class MediaService:
    def __init__(self, storage: ObjectStorage) -> None:
        self._storage = storage

    def fetch(self, key: str) -> bytes:
        return self._storage.get(key)
```

## Dependencies

- `PostgreSQL` — transactional data storage via SQLAlchemy
- `OpenTelemetry Collector` — receives traces via OTLP/gRPC when `otel_enabled=True`

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string | required |
| `AUTH_JWT_PUBLIC_KEY` | PEM-encoded RSA public key for JWT validation | required |
| `AUTH_JWT_ALGORITHM` | JWT signing algorithm | `RS256` |
| `AUTH_JWT_AUDIENCE` | Expected JWT audience claim | `None` |
| `OTEL_SERVICE_NAME` | Service name reported in traces | required |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector gRPC endpoint | `http://localhost:4317` |
| `OTEL_ENABLED` | Enable OTLP trace export | `True` |
