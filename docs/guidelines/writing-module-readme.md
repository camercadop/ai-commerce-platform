# Writing a Module README

How to write the `README.md` for a domain module under `app/`.

See [domain-module.md](domain-module.md) for the full module scaffolding process.

---

## Sections

Every README must include the sections below in this order. Omit a section only
if it genuinely does not apply (e.g. no Events section if the module publishes nothing).

### Header

One paragraph. State what the domain manages and what it delegates. No bullet points.

### Responsibilities

Bullet list of domain actions. Write in the imperative. No implementation details.

### Module layout

File tree with a one-line description per entry. Descriptions must say what the file
**is** (its role), not what it contains. Do not list classes, functions, or filenames
in the description.

### Request flow

Sequence diagram from HTTP request to database and back. Only include layers that
exist in the module.

### Endpoints

Table of all endpoints. Follow the table with:

- Usage examples for endpoints with non-obvious behavior only (e.g. upsert semantics,
  ownership linking, flag side effects). Skip examples for straightforward CRUD.
- An error responses subsection with the full HTTP status → error code mapping.

### Authorization

Only include if the module enforces ownership or custom access rules. Describe the
rule in prose and illustrate with a flowchart. Always explain why `404` is returned
instead of `403` when applicable.

### Events

For each published event:

- A table with event name, topic, and trigger.
- A sequence diagram of the publish flow.
- The full `data` payload schema.
- The envelope fields relevant to consumers (`event_type`, `version`, `producer`,
  `aggregate_type`, `aggregate_id`).
- The versioning contract: consumers must check `event_type` and `version` before
  deserializing `data`. `version` is incremented only on breaking changes.

Do not document consumed events here — that belongs in the consumer's README.

### Data model

Table of owned tables and an ER diagram. Note soft-delete behavior if applicable.

### Dependencies

Table of runtime dependencies. Mark each as required or optional. For optional
dependencies, describe the degraded behavior when unavailable.

### Application setup, Configuration, Running migrations, Running tests

Standard closing sections. Keep them short.

---

## Rules

- Section order must follow this document.
- Module layout descriptions say what a file **is**, not what it contains.
- Usage examples only for endpoints with non-obvious behavior.
- Event payload schema must always be documented for every published event.
- Do not document consumed events in the publisher's README.

---

## Template

```markdown
# <Domain>

Manages [...]. <Concern> is delegated to [...].

## Responsibilities

- <Action> [...]
- <Action> [...]

## Module layout

app/<domain>/
├── app.py          # Application factory
├── routes.py       # HTTP layer
├── schemas.py      # Public API contracts
├── service.py      # Domain logic
├── repository.py   # Data access layer
├── models.py       # ORM models
├── events.py       # Domain events
├── exceptions.py   # Domain-specific exceptions
├── migrations/     # Database migrations
└── tests/          # Test suite

## Request flow

sequenceDiagram
    Client->>Routes: HTTP request + Bearer JWT
    Routes->>Routes: Validate JWT & ownership
    Routes->>Service: Call domain method
    Service->>Repository: Query / persist
    Repository->>DB: SQL
    DB-->>Repository: Result
    Repository-->>Service: ORM model
    Service-->>Routes: Domain object
    Routes-->>Client: JSON response

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/<resource>` | [...] |
| `GET` | `/api/v1/<resource>/{id}` | [...] |

All endpoints require a valid Bearer JWT.

**<Example title>** — <one sentence on the non-obvious behavior>.

curl -X POST /api/v1/<resource> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ ... }'

### Error responses

{ "code": "<ERROR_CODE>", "message": "<description>" }

| Status | Code | Trigger |
| --- | --- | --- |
| `401` | — | Missing or invalid JWT |
| `404` | `<RESOURCE>_NOT_FOUND` | [...] |
| `409` | `<RESOURCE>_ALREADY_EXISTS` | [...] |

## Authorization

[Ownership rule. Explain why 404 is returned instead of 403.]

flowchart TD
    A[Request] --> B[Decode JWT]
    B --> C{Valid signature?}
    C -- No --> D[401 Unauthorized]
    C -- Yes --> E[Load resource by ID]
    E --> F{Caller owns resource?}
    F -- No --> G[404 Not Found]
    F -- Yes --> H[Proceed]

## Events

| Event | Topic | Trigger |
| --- | --- | --- |
| `<EventName>` | `<domain>.<resource>.<past-tense>` | [...] |

sequenceDiagram
    Service->>Events: publish_*(broker, aggregate)
    Events->>Broker: publish("<topic>", EventEnvelope)
    Broker-->>Consumers: <EventName> event

### <EventName> payload

| Field | Type | Description |
| --- | --- | --- |
| `<field>` | `<type>` | [...] |

Envelope fields relevant to consumers:

| Field | Value |
| --- | --- |
| `event_type` | `<EventName>` |
| `version` | `1` |
| `producer` | `<domain>` |
| `aggregate_type` | `<resource>` |
| `aggregate_id` | resource UUID |

`version` is incremented only on breaking changes. Consumers must check `event_type`
and `version` before deserializing `data`.

## Data model

| Table | Description |
| --- | --- |
| `<domain>_<resource>` | [...] |

erDiagram
    <Resource> {
        uuid id PK
        string field
        datetime deleted_at
    }

## Dependencies

| Dependency | Purpose | Required |
| --- | --- | --- |
| PostgreSQL | Primary data store | Yes |
| <Provider> | [...] | Yes |
| Message broker | Publishes domain events | No — [degraded behavior] |

## Application setup

from app.<domain>.app import create_app
...

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `<SETTING>` | [...] | required |

## Running migrations

uv run alembic -c app/<domain>/migrations/alembic.ini upgrade head

## Running tests

uv run pytest app/<domain>/tests/
```
