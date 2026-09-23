import logging
import uuid
from typing import Any

from app.shared.events import MessageBroker
from app.shared.events.envelope import EventEnvelope
from app.shared.observability import current_trace_id

logger = logging.getLogger(__name__)

_DOMAIN = "inventory"
_VERSION = 1


def _publish(broker: MessageBroker, topic: str, envelope: EventEnvelope) -> None:
    """Publish an event envelope to the broker, best-effort.

    Logs a warning on failure and never raises to the caller. Use this for
    all inventory event publishing to ensure domain transactions are never
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


def publish_inventory_reserved(
    broker: MessageBroker,
    reservation_id: uuid.UUID,
    variant_id: uuid.UUID,
    order_id: uuid.UUID,
    quantity: int,
) -> None:
    """Publish an InventoryReserved event.

    Call after inventory stock is reserved for an order. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        reservation_id: UUID of the reservation.
        variant_id: UUID of the product variant.
        order_id: UUID of the order requesting the reservation.
        quantity: Number of units reserved.
    """
    data: dict[str, Any] = {
        "reservation_id": str(reservation_id),
        "variant_id": str(variant_id),
        "order_id": str(order_id),
        "quantity": quantity,
    }
    _publish(
        broker,
        "inventory.stock.reserved",
        EventEnvelope(
            event_type="InventoryReserved",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="inventory_item",
            aggregate_id=str(variant_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_inventory_released(
    broker: MessageBroker,
    reservation_id: uuid.UUID,
    variant_id: uuid.UUID,
    order_id: uuid.UUID,
    quantity: int,
) -> None:
    """Publish an InventoryReleased event.

    Call when a stock reservation is released (payment failure). Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        reservation_id: UUID of the reservation.
        variant_id: UUID of the product variant.
        order_id: UUID of the order releasing the reservation.
        quantity: Number of units released.
    """
    data: dict[str, Any] = {
        "reservation_id": str(reservation_id),
        "variant_id": str(variant_id),
        "order_id": str(order_id),
        "quantity": quantity,
    }
    _publish(
        broker,
        "inventory.stock.released",
        EventEnvelope(
            event_type="InventoryReleased",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="inventory_item",
            aggregate_id=str(variant_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_inventory_confirmed(
    broker: MessageBroker,
    reservation_id: uuid.UUID,
    variant_id: uuid.UUID,
    order_id: uuid.UUID,
    quantity: int,
) -> None:
    """Publish an InventoryConfirmed event.

    Call when a stock reservation is confirmed (payment success). Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        reservation_id: UUID of the reservation.
        variant_id: UUID of the product variant.
        order_id: UUID of the order confirming the reservation.
        quantity: Number of units confirmed.
    """
    data: dict[str, Any] = {
        "reservation_id": str(reservation_id),
        "variant_id": str(variant_id),
        "order_id": str(order_id),
        "quantity": quantity,
    }
    _publish(
        broker,
        "inventory.stock.confirmed",
        EventEnvelope(
            event_type="InventoryConfirmed",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="inventory_item",
            aggregate_id=str(variant_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )
