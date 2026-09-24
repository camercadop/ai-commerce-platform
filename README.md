# AI Commerce Platform

![CI](https://github.com/camercadop/ai-commerce-platform/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.14-blue)

A cloud-agnostic, API-first, AI-powered e-commerce platform combining conventional
commerce capabilities with modern AI application engineering.

## Purpose

A production-oriented backend platform that combines conventional e-commerce capabilities
with modern AI application engineering — product catalog, search, orders, payments,
and an AI shopping agent built on top of an event-driven, cloud-agnostic architecture.

## Architecture

The platform is organized as a monorepo of domain modules under `app/`, each
owning its data and business logic. A shared infrastructure layer (`app/shared/`)
provides platform primitives with no business logic.

```
app/
├── shared/     # Platform infrastructure (auth, db, events, observability, storage, audit_log)
├── sys_audit/  # Audit log implementation
├── identity/   # Customer profiles and addresses
├── catalog/    # Product catalog (categories, brands, products, variants)
├── cart/       # Shopping carts and line items
├── orders/     # Checkout and order management
└── inventory/  # Stock and reservations
```

See [docs/architecture.md](docs/architecture.md) for the full system design and [docs/adr/](docs/adr/) for
architectural decisions.

## Tech stack

- **Runtime**: Python 3.14, FastAPI, Pydantic, SQLAlchemy
- **Database**: PostgreSQL (via Alembic migrations)
- **Audit log**: MongoDB (via pymongo, abstract port)
- **Auth**: OIDC-compliant provider (JWT validation, provider-agnostic)
- **API Gateway**: Kong (db-less, declarative config, JWT + rate limiting + CORS)
- **Cache / rate limiting**: Redis
- **Observability**: OpenTelemetry, structured logging
- **Storage**: MinIO / S3-compatible (abstract port)

## Local setup

**Prerequisites**: Python 3.14, [uv](https://docs.astral.sh/uv/), Docker

```bash
cp .env.example .env              # configure environment variables
docker compose up -d postgres     # start database only
uv sync                           # install dependencies
```

To start the full stack including Kong and all domain services:

```bash
docker compose up -d
```

Run migrations for each domain (each owns its own Alembic config):

```bash
uv run alembic -c app/<domain>/migrations/alembic.ini upgrade head
```

## Development

```bash
uv run ruff check .         # lint
uv run ruff format .        # format
uv run mypy app/            # type check
uv run pytest               # run tests
```

Pre-commit hooks run all checks automatically on commit:

```bash
uv run pre-commit install
```

## Testing

Tests require a running PostgreSQL instance. The test database is created
automatically on the first run:

```bash
uv run pytest
```

## Documentation

| Path | Description |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | System design and service boundaries |
| [docs/adr/](docs/adr/) | Architectural Decision Records |
| [docs/guidelines/](docs/guidelines/) | Coding and design guidelines |
| [docs/development.md](docs/development.md) | Developer workflow |


## License

Licensed under the [Apache License 2.0](LICENSE).
