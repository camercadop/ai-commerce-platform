from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Platform-level wrapper for all domain events.

    Every event published to the broker must be wrapped in this envelope.
    Consumers must use event_type and version to route and deserialize the
    payload — never inspect the data field directly without first checking
    the event_type.

    Fields:
        event_id: Unique identifier for this event instance. Used for deduplication.
        event_type: PascalCase past-tense domain fact (e.g. ProductCreated).
        version: Payload schema version. Increment only on breaking changes.
        occurred_at: UTC timestamp of when the event occurred in the domain.
        producer: Name of the domain that published this event.
        aggregate_type: The domain entity this event is about (e.g. product).
        aggregate_id: The identifier of the aggregate instance.
        trace_id: Propagated trace context for end-to-end correlation (ADR-005).
        data: The event payload. Shape is defined by event_type and version.
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    version: int
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    producer: str
    aggregate_type: str
    aggregate_id: str
    trace_id: str
    data: dict[str, Any]
