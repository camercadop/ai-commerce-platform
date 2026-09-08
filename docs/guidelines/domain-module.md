# Domain Module

How to create a new domain module in this project.

See [ADR-001: Service Boundaries and Domain Ownership](../adr/001-service-boundaries-and-domain-ownership.md) and
[docs/architecture.md](../architecture.md) for the structural rationale.

---

## 1. Scaffold the domain

Create the domain directory under `app/`. Not every file is required — use the table
below to decide what applies.

| File | Required when |
| --- | --- |
| `README.md` | Always |
| `app.py` | Always — exposes `create_app()` |
| `routes.py` | The domain exposes HTTP endpoints |
| `schemas.py` | The domain exposes HTTP endpoints |
| `service.py` | The domain has business logic |
| `repository.py` | The domain has a database |
| `models.py` | The domain has a database |
| `events.py` | The domain publishes or consumes Kafka events |
| `migrations/` | The domain has a database |
| `tests/` | Always |

Full layout of a domain with all files:

```
app/<domain>/
├── README.md
├── app.py
├── routes.py
├── schemas.py
├── service.py
├── repository.py
├── models.py
├── events.py
├── migrations/
│   ├── env.py
│   ├── alembic.ini
│   └── versions/
└── tests/
    ├── conftest.py
    ├── fakes.py
    └── factories.py
```

## 2. Implement `create_app()`

Every domain exposes a `create_app()` factory that returns a configured FastAPI app.

```python
# app/<domain>/app.py
from fastapi import FastAPI
from app.<domain>.routes import router

def create_app() -> FastAPI:
    """Create and configure the <domain> FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    return app
```

## 3. Write the README

Every domain `README.md` must cover:

- What the domain is responsible for.
- What data it owns.
- What endpoints it exposes.
- What events it publishes.
- What events it consumes.
- What external dependencies it requires.
- What configuration it expects.

```markdown
# <Domain>

Responsible for [...].

## Owned Data

- [list of models]

## Endpoints

- `POST /api/v1/<resource>` — [...]
- `GET /api/v1/<resource>/{id}` — [...]

## Published Events

- `EventName` — emitted when [...]

## Consumed Events

- `EventName` — triggers [...]

## Dependencies

- `PostgreSQL` — [...]
- `Kafka` — [...]

## Configuration

- `SETTING_NAME` — description, expected values
```

## 4. Set up the migration environment

Each domain with a database has its own Alembic environment under `app/<domain>/migrations/`.

```
app/<domain>/migrations/
├── env.py
├── alembic.ini
└── versions/
```

Run migrations for a specific domain by pointing Alembic at the domain's config:

```bash
uv run alembic -c app/<domain>/migrations/alembic.ini upgrade head
```

See `docs/development.md` for the full migration workflow.

---

## Rules

- Every domain module must have a `README.md`.
- Every domain must expose a `create_app()` factory in `app.py`.
- No domain may import from another domain's internals.
- Every domain with a database must have its own Alembic environment under `app/<domain>/migrations/`.
- Every domain must have a `tests/` directory under `app/<domain>/`.
