# Architecture

Implementation-level structural decisions for the AI Commerce Platform.

This document covers folder layout, module conventions, and shared layer boundaries.
Foundational architectural principles live in `docs/adr/`.
Developer workflow lives in `docs/development.md`.

---

## Project Structure

```
ai-commerce-platform/
├── app/
│   ├── catalog/
│   │   ├── migrations/
│   │   └── tests/
│   ├── commerce/
│   │   ├── migrations/
│   │   └── tests/
│   ├── inventory/
│   │   ├── migrations/
│   │   └── tests/
│   ├── payment/
│   │   ├── migrations/
│   │   └── tests/
│   ├── identity/
│   │   ├── migrations/
│   │   └── tests/
│   ├── ai_agent/
│   │   └── tests/
│   ├── search/
│   │   └── tests/
│   ├── media/
│   │   └── tests/
│   ├── notification/
│   │   └── tests/
│   ├── shopify/
│   │   └── tests/
│   ├── audit/
│   │   └── tests/
│   └── shared/
│       ├── api/
│       ├── config/
│       ├── db/
│       ├── events/
│       ├── observability/
│       ├── auth/
│       └── storage/
├── notebooks/
├── infra/
│   ├── k8s/
│   ├── terraform/
│   └── docker/
├── docs/
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
├── routes.py       # APIRouter with all endpoints
├── schemas.py      # Pydantic request/response models
├── service.py      # Business logic
├── repository.py   # Database access
├── models.py       # SQLAlchemy models
└── events.py       # Kafka producers and consumers for this domain
```

Not every file is required for every domain. A domain without Kafka interaction omits `events.py`. A domain without a database omits `models.py` and `repository.py`.

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
| `api/` | Uniform response envelope and error schemas (ADR-014) |
| `config/` | Pydantic Settings base class, startup validation (ADR-015) |
| `db/` | SQLAlchemy engine setup and session factory |
| `events/` | Kafka producer/consumer base, event envelope Pydantic model |
| `observability/` | OpenTelemetry setup, structured logging, metrics |
| `auth/` | JWT validation, auth middleware, token claims extraction |
| `storage/` | ObjectStorage abstraction and MinIO/S3 implementation (ADR-004) |

---

## Configuration

Each domain defines its own Pydantic Settings class. All domain settings are composed and validated at application startup. A missing or invalid configuration value causes startup to fail with an explicit error (ADR-015).

No domain may read environment variables directly outside of its Settings class.

---

## Migrations

Each domain has its own Alembic environment under `app/<domain>/migrations/`, with its own `env.py`, `alembic.ini`, and `versions/` directory. Migration histories are never shared across domains.

This enforces data ownership (ADR-001) at the migration level and ensures that extracting a domain into a separate service requires no migration history untangling.

See `docs/development.md` for the migration workflow.
