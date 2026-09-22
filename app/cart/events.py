import logging
import uuid
from typing import Any, TypedDict

from app.shared.events import EventEnvelope, MessageBroker
from app.shared.observability import current_trace_id

logger = logging.getLogger(__name__)

_DOMAIN = "cart"
_VERSION = 1


class CartItemDetailsData(TypedDict):
    """Quantity and pricing details for a cart item mutation event."""

    quantity: int
    unit_price: str


def _publish(broker: MessageBroker, topic: str, envelope: EventEnvelope) -> None:
    """Publish an event envelope to the broker, best-effort.

    Logs a warning on failure and never raises to the caller. Use this for
    all cart event publishing to ensure domain transactions are never
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


def publish_cart_created(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    session_id: str,
    customer_id: uuid.UUID | None = None,
) -> None:
    """Publish a CartCreated event.

    Call after a cart is successfully persisted. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the newly created cart.
        session_id: Session token for the cart.
        customer_id: Optional UUID of the authenticated customer.
    """
    data: dict[str, Any] = {
        "session_id": session_id,
        "customer_id": str(customer_id) if customer_id else None,
    }
    _publish(
        broker,
        "cart.cart.created",
        EventEnvelope(
            event_type="CartCreated",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_cart_item_added(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    variant_id: uuid.UUID,
    item_details: CartItemDetailsData,
) -> None:
    """Publish a CartItemAdded event.

    Call after a cart item is successfully added. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the cart.
        item_id: UUID of the newly added cart item.
        variant_id: UUID of the product variant.
        item_details: Quantity and unit price details for the cart item.
    """
    data: dict[str, Any] = {
        "item_id": str(item_id),
        "variant_id": str(variant_id),
        "quantity": item_details["quantity"],
        "unit_price": item_details["unit_price"],
    }
    _publish(
        broker,
        "cart.item.added",
        EventEnvelope(
            event_type="CartItemAdded",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_cart_item_updated(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    variant_id: uuid.UUID,
    item_details: CartItemDetailsData,
) -> None:
    """Publish a CartItemUpdated event.

    Call after a cart item quantity is successfully updated. Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the cart.
        item_id: UUID of the updated cart item.
        variant_id: UUID of the product variant.
        item_details: Quantity and unit price details for the cart item.
    """
    data: dict[str, Any] = {
        "item_id": str(item_id),
        "variant_id": str(variant_id),
        "quantity": item_details["quantity"],
        "unit_price": item_details["unit_price"],
    }
    _publish(
        broker,
        "cart.item.updated",
        EventEnvelope(
            event_type="CartItemUpdated",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_cart_item_removed(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> None:
    """Publish a CartItemRemoved event.

    Call after a cart item is successfully removed. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the cart.
        item_id: UUID of the removed cart item.
        variant_id: UUID of the product variant.
    """
    data: dict[str, Any] = {
        "item_id": str(item_id),
        "variant_id": str(variant_id),
    }
    _publish(
        broker,
        "cart.item.removed",
        EventEnvelope(
            event_type="CartItemRemoved",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_cart_item_unavailable(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> None:
    """Publish a CartItemUnavailable event.

    Call when a cart item is marked unavailable due to inventory or catalog
    constraints. The item is kept in-place with updated status. Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the cart.
        item_id: UUID of the affected cart item.
        variant_id: UUID of the product variant.
    """
    data: dict[str, Any] = {
        "item_id": str(item_id),
        "variant_id": str(variant_id),
    }
    _publish(
        broker,
        "cart.item.unavailable",
        EventEnvelope(
            event_type="CartItemUnavailable",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_cart_cleared(broker: MessageBroker, cart_id: uuid.UUID) -> None:
    """Publish a CartCleared event.

    Call after all items are removed from a cart. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the cleared cart.
    """
    _publish(
        broker,
        "cart.cart.cleared",
        EventEnvelope(
            event_type="CartCleared",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data={},
        ),
    )


def publish_cart_merged(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    source_session_id: str,
    merged_count: int,
) -> None:
    """Publish a CartMerged event.

    Call after an anonymous cart is merged into a customer cart. Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the target customer cart.
        source_session_id: Session token of the merged anonymous cart.
        merged_count: Number of items merged into the customer cart.
    """
    data: dict[str, Any] = {
        "source_session_id": source_session_id,
        "merged_count": merged_count,
    }
    _publish(
        broker,
        "cart.cart.merged",
        EventEnvelope(
            event_type="CartMerged",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_cart_updated(
    broker: MessageBroker,
    cart_id: uuid.UUID,
    mutation: str,
    items_count: int,
) -> None:
    """Publish a CartUpdated coarse sync event.

    Published on every cart mutation (add, update, remove, clear, merge) for
    downstream consumers. Best-effort — failure logs a warning and does not
    affect the domain transaction.

    Args:
        broker: The message broker port.
        cart_id: UUID of the cart.
        mutation: The mutation that triggered this event (e.g. item_added,
            item_updated, item_removed, cart_cleared, cart_merged).
        items_count: Current number of active items in the cart.
    """
    data: dict[str, Any] = {
        "mutation": mutation,
        "items_count": items_count,
    }
    _publish(
        broker,
        "cart.cart.updated",
        EventEnvelope(
            event_type="CartUpdated",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="cart",
            aggregate_id=str(cart_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )
