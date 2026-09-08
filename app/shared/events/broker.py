import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from app.shared.events.envelope import EventEnvelope

logger = logging.getLogger(__name__)


class MessageBroker(ABC):
    """Abstract port for publishing and consuming domain events.

    All concrete implementations of this port live within the domain module
    that requires them (e.g. app/catalog/events.py). Domain code must never
    depend on a concrete broker implementation directly (ADR-004).

    Use publish to emit events from a domain's events.py.
    Use subscribe to register a consumer handler for a given topic.
    """

    @abstractmethod
    def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Publish an event envelope to the given topic.

        The topic naming convention is <domain>.<aggregate>.<event_type>
        in lowercase (e.g. catalog.product.created).

        Args:
            topic: The broker topic to publish to.
            envelope: The fully constructed event envelope.
        """

    @abstractmethod
    def subscribe(self, topic: str, handler: Callable[[EventEnvelope], None]) -> None:
        """Register a handler to be called for each event on the given topic.

        Handlers must be idempotent — processing the same envelope twice
        must produce the same outcome as processing it once (ADR-011).

        Args:
            topic: The broker topic to subscribe to.
            handler: Callable that receives a deserialized EventEnvelope.
        """
