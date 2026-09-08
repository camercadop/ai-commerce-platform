# Event Design

How to define, publish, and consume domain events consistently across all domains.

See [ADR-011: Operation Safety](../adr/011-operation-safety.md) and
[ADR-002: API-First Design](../adr/002-api-first-design.md) for the architectural rationale.

The current message broker implementation is Kafka, accessed through the abstraction
defined in `shared/events/` (ADR-004). The guidelines below apply regardless of the
underlying broker.

---

## 1. Define the AsyncAPI contract and Pydantic model together

Every new event requires both in the same change:

- An AsyncAPI spec entry in `docs/` describing the event contract.
- A Pydantic model in `shared/events/` or the domain's `events.py` representing the payload.

Neither may exist without the other.

## 2. Use the platform event envelope

Every event must be wrapped in the platform envelope defined in `shared/events/`.

```python
class EventEnvelope(BaseModel):
    event_id: UUID
    event_type: str
    version: int
    occurred_at: datetime
    producer: str
    aggregate_type: str
    aggregate_id: str
    trace_id: str
    data: dict[str, Any]
```

## 3. Name events as past-tense domain facts

Event names are `PascalCase`, past tense, scoped to the domain.

```
ProductCreated
OrderPlaced
PaymentSucceeded
InventoryReserved
```

## 4. Version events explicitly

When a breaking change to an event payload is required, introduce a new version.
The old version must remain published until all consumers have migrated.

```
ProductUpdated.v1
ProductUpdated.v2
```

## 5. Publish events through the domain's `events.py`

Each domain owns its event producers. No domain may publish events on behalf of another domain.

```python
# catalog/events.py
def publish_product_created(product: Product) -> None:
    envelope = EventEnvelope(
        event_type="ProductCreated",
        version=1,
        producer="catalog",
        aggregate_type="product",
        aggregate_id=str(product.id),
        data=ProductCreatedPayload.from_product(product).model_dump(),
        ...
    )
    broker.publish("catalog.product.created", envelope)
```

## 6. Write idempotent consumers

Every consumer must deduplicate at the handler boundary. Processing the same event
twice must produce the same outcome as processing it once (ADR-011).

```python
def handle_product_created(envelope: EventEnvelope) -> None:
    if product_repository.exists(envelope.aggregate_id):
        return
    ...
```

---

## Rules

- Every event must have both an AsyncAPI contract and a Pydantic model, created in the same change.
- Every event must use the platform envelope from `shared/events/`.
- Event names must be past-tense, PascalCase domain facts.
- Breaking payload changes require a new event version. The old version must remain available until all consumers migrate.
- Every consumer must be idempotent — processing the same event twice must produce the same result.
- A domain must never publish events on behalf of another domain.
