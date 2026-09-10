# Identity

Manages customer profiles and addresses. Authentication is delegated to an external
identity provider (e.g. Keycloak). This domain owns domain-specific customer data
linked to the provider via the JWT `sub` claim.

## Responsibilities

- Register customer profiles on first login
- Store and update customer profile data (name, email)
- Manage customer addresses
- Manage customer preferences (key-value store)
- Publish `CustomerRegistered` events on new registrations

## Module layout

```
app/identity/
├── app.py          # FastAPI application factory
├── routes.py       # Route handlers and exception handlers
├── schemas.py      # Request and response Pydantic schemas
├── service.py      # CustomerService, AddressService
├── repository.py   # CustomerRepository, AddressRepository
├── models.py       # Customer, Address, CustomerPreference ORM models
├── events.py       # CustomerRegistered event and publish helper
├── exceptions.py   # Domain exceptions
├── migrations/     # Alembic environment and migration versions
└── tests/          # Unit and integration tests
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/customers` | Register a new customer profile |
| `GET` | `/api/v1/customers/{id}` | Get a customer profile |
| `PATCH` | `/api/v1/customers/{id}` | Update a customer profile |
| `DELETE` | `/api/v1/customers/{id}` | Soft-delete a customer profile |
| `PATCH` | `/api/v1/customers/{id}/preferences` | Upsert customer preferences |
| `GET` | `/api/v1/customers/{id}/addresses` | List customer addresses |
| `POST` | `/api/v1/customers/{id}/addresses` | Add a new address |
| `PATCH` | `/api/v1/customers/{id}/addresses/{addr_id}` | Update an address |
| `DELETE` | `/api/v1/customers/{id}/addresses/{addr_id}` | Soft-delete an address |

All endpoints require a valid Bearer JWT. Ownership is enforced on every request —
a customer can only access their own profile and addresses.

## Authorization

Ownership is checked by matching the JWT `sub` claim against `Customer.identity_provider_id`.
A mismatch returns `404` (not `403`) to avoid leaking resource existence to unauthorized callers.

## Events

| Event | Topic | Trigger |
| --- | --- | --- |
| `CustomerRegistered` | `identity.customer.registered` | New customer profile created |

## Data model

| Table | Description |
| --- | --- |
| `identity_customers` | Customer profiles linked to the identity provider |
| `identity_customer_addresses` | Physical addresses per customer |
| `identity_customer_preferences` | Key-value preferences per customer |

`Customer` and `Address` support soft delete via `deleted_at`. All queries exclude
soft-deleted records automatically.

## Application setup

```python
from app.identity.app import create_app
from app.shared.auth import AuthSettings
from app.shared.db import DatabaseSettings

app = create_app(
    db_settings=DatabaseSettings(),
    auth_settings=AuthSettings(),
)
```

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | required |
| `AUTH_JWT_PUBLIC_KEY` | PEM-encoded RSA public key for JWT validation | required |
| `AUTH_JWT_ALGORITHM` | JWT signing algorithm | `RS256` |
| `AUTH_JWT_AUDIENCE` | Expected JWT audience claim | `None` |

## Running migrations

```bash
uv run alembic -c app/identity/migrations/alembic.ini upgrade head
```

## Running tests

```bash
uv run pytest app/identity/tests/
```

Tests require a running PostgreSQL instance with a `commerce_test` database.
