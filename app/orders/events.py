import logging
import uuid
from decimal import Decimal
from typing import Any, TypedDict

from app.shared.events import EventEnvelope, MessageBroker
from app.shared.observability import current_trace_id

logger = logging.getLogger(__name__)

_DOMAIN = "orders"
_VERSION = 1


class OrderPlacedData(TypedDict):
    """Payload for an order placement event."""

    order_id: str
    cart_id: str
    customer_id: str | None
    total_amount: str
    items_count: int


def _publish(broker: MessageBroker, topic: str, envelope: EventEnvelope) -> None:
    """Publish an event envelope to the broker, best-effort.

    Logs a warning on failure and never raises to the caller. Use this for
    all order event publishing to ensure domain transactions are never
    rolled back due to broker unavailability.

    Args:
        broker: The message broker port.
        topic: Broker topic in <domain>.<aggregate>.<event> format.
        envelope: The fully constructed event envelope to publish.
    """
    try:
        broker.publish(topic, envelope)
    except Exception:
        logger.warning(
            "Failed to publish event %s for aggregate %s",
            envelope.event_type,
            envelope.aggregate_id,
        )


def publish_order_placed(
    broker: MessageBroker,
    order_id: uuid.UUID,
    cart_id: uuid.UUID,
    customer_id: uuid.UUID | None,
    total_amount: Decimal,
    items_count: int,
) -> None:
    """Publish an OrderPlaced event.

    Call after an order is successfully created. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        order_id: UUID of the newly created order.
        cart_id: UUID of the cart that was checked out.
        customer_id: Optional UUID of the customer who placed the order.
        total_amount: Total amount of the order.
        items_count: Number of items in the order.
    """
    data: dict[str, Any] = {
        "order_id": str(order_id),
        "cart_id": str(cart_id),
        "customer_id": str(customer_id) if customer_id else None,
        "total_amount": str(total_amount),
        "items_count": items_count,
    }
    _publish(
        broker,
        "orders.order.placed",
        EventEnvelope(
            event_type="OrderPlaced",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="order",
            aggregate_id=str(order_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )
