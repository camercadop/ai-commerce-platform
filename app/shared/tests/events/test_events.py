from collections.abc import Callable
from uuid import UUID

import pytest

from app.shared.events import EventEnvelope, MessageBroker


class InMemoryBroker(MessageBroker):
    """In-memory broker for testing event publishing and consumption."""

    def __init__(self) -> None:
        self.published: list[tuple[str, EventEnvelope]] = []
        self._handlers: dict[str, list[Callable[[EventEnvelope], None]]] = {}

    def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Store the published envelope for assertion in tests."""
        self.published.append((topic, envelope))
        for handler in self._handlers.get(topic, []):
            handler(envelope)

    def subscribe(self, topic: str, handler: Callable[[EventEnvelope], None]) -> None:
        """Register a handler for the given topic."""
        self._handlers.setdefault(topic, []).append(handler)


@pytest.fixture()
def broker() -> InMemoryBroker:
    """Provide a fresh InMemoryBroker for each test."""
    return InMemoryBroker()


@pytest.fixture()
def envelope() -> EventEnvelope:
    """Provide a minimal valid EventEnvelope for each test."""
    return EventEnvelope(
        event_type="ProductCreated",
        version=1,
        producer="catalog",
        aggregate_type="product",
        aggregate_id="abc-123",
        trace_id="trace-xyz",
        data={"name": "Headphones", "price": "99.00"},
    )


def test_envelope_generates_event_id(envelope: EventEnvelope) -> None:
    assert isinstance(envelope.event_id, UUID)


def test_envelope_generates_occurred_at(envelope: EventEnvelope) -> None:
    assert envelope.occurred_at is not None


def test_envelope_stores_payload(envelope: EventEnvelope) -> None:
    assert envelope.data == {"name": "Headphones", "price": "99.00"}


def test_broker_publish_stores_event(
    broker: InMemoryBroker, envelope: EventEnvelope
) -> None:
    broker.publish("catalog.product.created", envelope)

    assert len(broker.published) == 1
    topic, stored = broker.published[0]
    assert topic == "catalog.product.created"
    assert stored.event_type == "ProductCreated"


def test_broker_subscribe_receives_published_event(
    broker: InMemoryBroker, envelope: EventEnvelope
) -> None:
    received: list[EventEnvelope] = []
    broker.subscribe("catalog.product.created", received.append)

    broker.publish("catalog.product.created", envelope)

    assert len(received) == 1
    assert received[0].aggregate_id == "abc-123"


def test_broker_subscribe_does_not_receive_other_topics(
    broker: InMemoryBroker, envelope: EventEnvelope
) -> None:
    received: list[EventEnvelope] = []
    broker.subscribe("catalog.product.updated", received.append)

    broker.publish("catalog.product.created", envelope)

    assert len(received) == 0
