# Architecture

Implementation-level structural decisions for the AI Commerce Platform.

This document covers folder layout, module conventions, and shared layer boundaries.

Foundational architectural principles live in `docs/adr/`.
Developer workflow lives in `docs/development.md`.

---

## C4 Level 0 — System Context

```mermaid
flowchart TB
    shopper(["Shopper\nBrowses, searches, and places orders"])
    operator(["Operator\nManages catalog and monitors activity"])

    platform["AI Commerce Platform"]
    kong["Kong\nAPI Gateway"]

    mongo["MongoDB\nAudit log"]
    postgres["PostgreSQL\nTransactional data"]
    redis["Redis\nRate limit counters"]
    kafka["Kafka\nDomain events"]

    shopper -- "HTTPS / REST" --> kong
    operator -- "HTTPS / REST" --> kong
    kong -- "HTTP" --> platform
    platform -- "pymongo" --> mongo
    platform -- "SQLAlchemy" --> postgres
    platform -- "confluent-kafka" --> kafka
    kong -- "TCP" --> redis
```

---

## C4 Level 1 — Container Diagram

```mermaid
flowchart TB
    shopper(["Shopper"])
    operator(["Operator"])

    kong["Kong\nAPI Gateway\nAuth · Rate limiting · CORS"]

    subgraph platform ["AI Commerce Platform"]
        identity["Identity\nCustomer profiles & addresses"]
        catalog["Catalog\nCategories, brands, products, variants"]
        cart["Cart\nShopping carts & line items"]
        orders["Orders\nCheckout & order management"]
        inventory["Inventory\nStock & reservations"]
        sys_audit["sys_audit\nAudit log writer"]
        sys_eventbus["sys_eventbus\nKafka event bus"]
    end

    postgres["PostgreSQL\nTransactional data"]
    mongo["MongoDB\nAudit documents"]
    redis["Redis\nRate limit counters"]
    kafka["Kafka\nDomain events"]

    shopper -- "HTTPS / REST" --> kong
    operator -- "HTTPS / REST" --> kong
    kong -- "JWT auth" --> identity
    kong -- "public" --> catalog
    kong -- "JWT auth" --> cart
    kong -- "JWT auth" --> orders
    kong -- "JWT auth" --> inventory
    kong -- "TCP" --> redis

    cart -- "CatalogPort" --> catalog
    orders -- "CartPort (stub)" --> cart

    identity --> sys_audit
    catalog --> sys_audit
    cart --> sys_audit
    orders --> sys_audit
    inventory --> sys_audit
    sys_audit -- "pymongo" --> mongo

    catalog --> sys_eventbus
    cart --> sys_eventbus
    orders --> sys_eventbus
    inventory --> sys_eventbus
    sys_eventbus -- "confluent-kafka" --> kafka

    identity -- "SQLAlchemy" --> postgres
    catalog -- "SQLAlchemy" --> postgres
    cart -- "SQLAlchemy" --> postgres
    orders -- "SQLAlchemy" --> postgres
    inventory -- "SQLAlchemy" --> postgres
```

---

## C4 Level 2 — Component Diagram

```mermaid
flowchart LR
    shopper(["Shopper"])
    operator(["Operator"])

    subgraph identity ["Identity"]
        direction TB
        id_routes["routes"] --> id_service["service"]
        id_service --> id_repo["repository"]
        id_service --> id_events["events"]
        id_service --> id_audit["AuditPort"]
    end

    subgraph catalog ["Catalog"]
        direction TB
        cat_routes["routes"] --> cat_service["service"]
        cat_service --> cat_repo["repository"]
        cat_service --> cat_events["events"]
        cat_service --> cat_audit["AuditPort"]
        cat_service --> cat_broker["MessageBroker"]
    end

    subgraph cart ["Cart"]
        direction TB
        cart_routes["routes"] --> cart_service["service"]
        cart_service --> cart_repo["repository"]
        cart_service --> cart_events["events"]
        cart_service --> cart_audit["AuditPort"]
        cart_service --> cart_broker["MessageBroker"]
        cart_service --> cart_catalog["CatalogPort (stub)"]
        cart_service --> cart_inventory["InventoryPort (stub)"]
    end

    subgraph orders ["Orders"]
        direction TB
        ord_routes["routes"] --> ord_service["service"]
        ord_service --> ord_repo["repository"]
        ord_service --> ord_events["events"]
        ord_service --> ord_audit["AuditPort"]
        ord_service --> ord_broker["MessageBroker"]
        ord_service --> ord_cart["CartPort (stub)"]
        ord_service --> ord_adj["AdjustmentRulesPort (stub)"]
    end

    subgraph inventory ["Inventory"]
        direction TB
        inv_routes["routes"] --> inv_service["service"]
        inv_service --> inv_repo["repository"]
        inv_service --> inv_events["events"]
        inv_service --> inv_audit["AuditPort"]
        inv_service --> inv_broker["MessageBroker"]
    end

    subgraph infra ["Infrastructure"]
        direction TB
        sys_audit["sys_audit"] --> mongo["MongoDB"]
        sys_eventbus["sys_eventbus"] --> kafka["Kafka"]
        postgres["PostgreSQL"]
    end

    shopper --> id_routes
    shopper --> cat_routes
    shopper --> cart_routes
    shopper --> ord_routes
    shopper --> inv_routes
    operator --> cat_routes

    id_audit --> sys_audit
    cat_audit --> sys_audit
    cart_audit --> sys_audit
    ord_audit --> sys_audit
    inv_audit --> sys_audit

    cat_broker --> sys_eventbus
    cart_broker --> sys_eventbus
    ord_broker --> sys_eventbus
    inv_broker --> sys_eventbus

    id_repo --> postgres
    cat_repo --> postgres
    cart_repo --> postgres
    ord_repo --> postgres
    inv_repo --> postgres
```

---

## Project Structure

```
ai-commerce-platform/
├── app/
│   ├── identity/       # Customer profiles and addresses
│   ├── catalog/        # Product catalog
│   ├── cart/           # Shopping cart
│   ├── orders/         # Checkout & order management
│   ├── inventory/      # Stock & reservations
│   ├── sys_audit/      # Audit log implementation
│   ├── sys_eventbus/   # Kafka event bus implementation
│   └── shared/
│       ├── api/
│       ├── audit_log/
│       ├── auth/
│       ├── config/
│       ├── db/
│       ├── events/
│       ├── observability/
│       └── storage/
├── docker/
│   ├── kong/           # Kong entrypoint script
│   └── postgres/       # Postgres init scripts
├── kong/
│   └── kong.yml        # Kong declarative config (db-less)
├── docs/
├── Dockerfile          # Shared domain service image (DOMAIN build arg)
├── pyproject.toml
└── uv.lock
```

---

## Module Layout

Every domain module under `app/` follows this internal structure:

```
<domain>/
├── README.md
├── app.py          # create_app() factory — FastAPI app for this domain
├── container.py    # DeclarativeContainer — infrastructure singletons (audit, broker)
├── routes.py       # APIRouter with all endpoints and sentinel dependencies
├── schemas.py      # Pydantic request/response models
├── service.py      # Business logic
├── repository.py   # Database access
├── models.py       # SQLAlchemy models
├── exceptions.py   # Domain-specific exceptions extending shared base classes
├── events.py       # Domain event publishers
├── ports.py        # Abstract ports for external dependencies (optional)
└── adapters.py     # Concrete adapter implementations for ports (optional)
```

Not every file is required for every domain.

---

## Domain Conventions

- Each domain exposes a `create_app()` factory in `app.py`. A top-level entry point composes all domain apps for the monolith deployment.
- No domain may import from another domain's internals. Cross-domain data access goes through the owning domain's API or through events it publishes (ADR-001).
- Every domain must have a `README.md` describing its responsibility, owned data, published events, and consumed events.

---

## Shared Layer

`app/shared/` contains only platform infrastructure — no business logic. If a module in `shared/` starts depending on domain concepts (products, orders, customers), it belongs in a domain instead.

| Package | Responsibility |
| --- | --- |
| `api/` | Uniform response envelope, error schemas, pagination, validators (ADR-014) |
| `audit_log/` | Abstract audit port, `AuditRecord` schema, `record_audit()` helper, `NoOpAuditRepository` |
| `auth/` | JWT validation, auth middleware, token claims extraction |
| `config/` | Pydantic Settings base class, startup validation (ADR-015) |
| `db/` | SQLAlchemy engine, session factory, declarative base, mixins, generic repository |
| `events/` | Event envelope model, abstract `MessageBroker` port, `NoOpMessageBroker` |

`sys_audit/` and `sys_eventbus/` are concrete infrastructure modules that live outside `shared/` — they implement ports defined in `shared/` but carry provider-specific dependencies (`pymongo`, `confluent-kafka`). Domain code never imports from them directly; only composition roots (`app.py`) do.
| `exceptions.py` | Shared base exception classes (`ResourceNotFound`, `ResourceAlreadyExists`) |
| `observability/` | OpenTelemetry tracing setup, structured logging, `current_trace_id()` |
| `storage/` | Abstract `ObjectStorage` port (ADR-004) |

---

## Dependency Injection

Domains use `dependency-injector` (`DeclarativeContainer`) to manage infrastructure
singletons — `audit` and `broker` — that are shared across all requests within a
domain. Request-scoped objects (db session, services) remain under FastAPI's control.

Each domain's `routes.py` declares sentinel dependency functions (e.g. `_audit_dependency`,
`_broker_dependency`) that are never called directly. `app.py` overrides them at startup
via `app.dependency_overrides`, pulling resolved singletons from the container:

```python
from app.sys_audit import resolve_audit_repo
from app.sys_eventbus import resolve_broker

resolved_audit = audit_repo if audit_repo is not None else resolve_audit_repo()
resolved_broker = broker if broker is not None else resolve_broker()

container = CatalogContainer()
container.audit.override(resolved_audit)
container.broker.override(resolved_broker)
app.dependency_overrides[_audit_dependency] = lambda: container.audit()
```

Factory functions (`resolve_audit_repo`, `resolve_broker`) read the environment and return the appropriate concrete implementation or a no-op fallback. This keeps routes free of infrastructure construction logic and makes the wiring explicit and testable — tests pass no-op implementations directly without touching route code.

---

## Configuration

Each domain defines its own Pydantic Settings class. All domain settings are composed and validated at application startup. A missing or invalid configuration value causes startup to fail with an explicit error (ADR-015).

No domain may read environment variables directly outside of its Settings class.

---

## Migrations

Each domain has its own Alembic environment under `app/<domain>/migrations/`, with its own `env.py`, `alembic.ini`, and `versions/` directory. Migration histories are never shared across domains.

Each domain connects to its own PostgreSQL database (`commerce_<domain>`), provisioned automatically by `docker/postgres/init.sh` on container startup. This enforces data ownership (ADR-001) at the infrastructure level and ensures that extracting a domain into a separate service requires no database untangling.

All domain migration environments share a single `DATABASE_BASE_URL` (without the database name). Each `env.py` appends its own database name to build the full connection URL.

See `docs/development.md` for the migration workflow.
