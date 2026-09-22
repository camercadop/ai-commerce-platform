# Development

Developer workflow for the AI Commerce Platform.

This document covers local setup, tooling, and day-to-day development processes.
Structural and architectural decisions live in `docs/architecture.md`.

---

## Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Docker

---

## Local Setup

```bash
cp .env.example .env           # configure environment variables
docker compose up -d postgres  # start PostgreSQL
uv sync                        # install dependencies
uv run pre-commit install      # install pre-commit hooks
```

The Postgres container automatically provisions the following databases on first
startup via `docker/postgres/init.sh`:

| Database | Owner |
| --- | --- |
| `commerce` | default maintenance DB |
| `commerce_identity` | identity domain |

---

## Running the Stack

Start PostgreSQL only:

```bash
docker compose up -d postgres
```

Start PostgreSQL and MongoDB (required for audit log):

```bash
docker compose up -d postgres mongodb
```

Run the identity service locally:

```bash
uv run uvicorn app.identity.app:create_app --factory --reload
```

---

## Audit Log

The audit log uses MongoDB as its store. It is optional for local development —
when `MongoSettings` are not provided, a `NoOpAuditRepository` is used and audit
writes are silently skipped.

To enable audit logging locally, start MongoDB and set the following in `.env`:

```bash
MONGO_USERNAME=mongo
MONGO_PASSWORD=mongo
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=audit_log
```

Audit writes are best-effort — a failure logs a warning and never rolls back the
domain transaction. See [docs/adr/](adr/) for the full design rationale.

---

## Tooling

```bash
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy app/           # type check
```

Pre-commit hooks run all checks automatically on every commit:

```bash
uv run pre-commit install
```

---

## Guidelines

| Guideline | Description |
| --- | --- |
| [api-design.md](guidelines/api-design.md) | Response envelope, versioning, validation, pagination |
| [domain-module.md](guidelines/domain-module.md) | How to create a new domain module |
| [error-handling.md](guidelines/error-handling.md) | Domain exceptions, HTTP mapping, fallbacks, retry bounds |
| [event-design.md](guidelines/event-design.md) | Event envelope, naming, versioning, idempotent consumers |
| [writing-logs.md](guidelines/writing-logs.md) | Log levels, formatting, security events, sensitive data |
| [writing-models.md](guidelines/writing-models.md) | UUID PKs, timestamps, field comments, indexes, relationships |
| [writing-module-readme.md](guidelines/writing-module-readme.md) | Structure and content rules for domain module READMEs |
| [writing-tests.md](guidelines/writing-tests.md) | Test layers, dependency injection, fixtures, fakes |

---

## Migrations

Each domain manages its own Alembic environment under `app/<domain>/migrations/`.
All environments read `DATABASE_BASE_URL` from the environment and append the
domain-specific database name.

### Applying migrations

```bash
uv run alembic -c app/<domain>/migrations/alembic.ini upgrade head
```

### Generating a new migration

Ensure the database is running and all existing migrations are applied first:

```bash
docker compose up -d postgres
uv run alembic -c app/<domain>/migrations/alembic.ini upgrade head
uv run alembic -c app/<domain>/migrations/alembic.ini revision --autogenerate -m "<description>"
```

After autogenerate, always inspect the generated file and remove any operations
unrelated to the current change before applying.

### Confirming state

```bash
uv run alembic -c app/<domain>/migrations/alembic.ini current
```

---

## Testing

Tests require a running PostgreSQL instance. The test database (`commerce_test`)
is created automatically on the first run.

```bash
uv run pytest
```

To run with coverage:

```bash
uv run pytest --cov=app --cov-report=term-missing
```
