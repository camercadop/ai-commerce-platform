# events

Defines the abstract message broker port and the platform event envelope. Concrete
broker implementations live in the domain modules that require them. Domain code must
never depend on a concrete broker directly (ADR-004).

## Package layout

```
events/
├── __init__.py     # Public exports for the message broker port
├── broker.py       # Abstract message broker port and lifecycle contract
└── envelope.py     # Platform event envelope contract
```

## Public API

| Symbol | Description |
| --- | --- |
| `MessageBroker` | Abstract port for publishing and subscribing to domain events |
| `NoOpMessageBroker` | Discards all published events silently — use in tests and dev |
| `EventEnvelope` | Platform-level wrapper required for every published event |

### EventEnvelope fields

| Field | Type | Description |
| --- | --- | --- |
| `event_id` | `UUID` | Unique identifier for deduplication |
| `event_type` | `str` | PascalCase past-tense fact (e.g. `ProductCreated`) |
| `version` | `int` | Payload schema version; increment only on breaking changes |
| `occurred_at` | `datetime` | UTC timestamp of when the event occurred |
| `producer` | `str` | Domain that published the event |
| `aggregate_type` | `str` | Domain entity the event is about (e.g. `product`) |
| `aggregate_id` | `str` | Identifier of the affected aggregate instance |
| `trace_id` | `str` | OTel trace ID for end-to-end correlation |
| `data` | `dict[str, Any]` | Event payload; shape is defined by `event_type` and `version` |

## Lifecycle contract

`MessageBroker` implementations may require startup and shutdown actions, such as
opening connections or starting background consumer threads. The port exposes two
lifecycle methods for this purpose:

- `start()` — called once at application startup after configuration is complete.
- `stop()` — called once at application shutdown to drain in-flight work.

`NoOpMessageBroker` implements both methods as no-ops, so existing tests and local
development flows continue to work without changes. Concrete implementations in
`app/sys_eventbus/` provide the actual behavior.

## Consumer contract

Consumers must check `event_type` and `version` before deserializing `data`. Handlers
must be idempotent — processing the same envelope twice must produce the same outcome
as processing it once (ADR-011).

Topic naming convention: `<domain>.<aggregate>.<past-tense-verb>` in lowercase
(e.g. `catalog.product.created`).

```python
from app.shared.events import EventEnvelope, MessageBroker
from app.shared.observability import current_trace_id


def publish_product_created(broker: MessageBroker, product: Product) -> None:
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
