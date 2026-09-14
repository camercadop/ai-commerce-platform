import logging
import uuid
from decimal import Decimal
from typing import Any

from app.shared.events import EventEnvelope, MessageBroker
from app.shared.observability import current_trace_id

logger = logging.getLogger(__name__)

_DOMAIN = "catalog"
_VERSION = 1


def _publish(broker: MessageBroker, topic: str, envelope: EventEnvelope) -> None:
    """Publish an event envelope to the broker, best-effort.

    Logs a warning on failure and never raises to the caller. Use this for
    all catalog event publishing to ensure domain transactions are never
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


def publish_product_created(
    broker: MessageBroker,
    product_id: uuid.UUID,
    sku: str,
    name: str,
    base_price: Decimal,
    status: str,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    description: str | None = None,
    specs: dict[str, str] | None = None,
) -> None:
    """Publish a ProductCreated event.

    Call after a product is successfully persisted. Best-effort — failure
    logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        product_id: UUID of the newly created product.
        sku: Stock-keeping unit of the product.
        name: Display name of the product.
        base_price: Listed price of the product.
        status: Lifecycle status (draft, active, archived).
        category_id: Optional UUID of the assigned category.
        brand_id: Optional UUID of the assigned brand.
        description: Optional product description.
        specs: Optional free-form metadata map.
    """
    data: dict[str, Any] = {
        "sku": sku,
        "name": name,
        "base_price": str(base_price),
        "status": status,
        "category_id": str(category_id) if category_id else None,
        "brand_id": str(brand_id) if brand_id else None,
        "description": description,
        "specs": specs,
    }
    _publish(
        broker,
        "catalog.product.created",
        EventEnvelope(
            event_type="ProductCreated",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="product",
            aggregate_id=str(product_id),
            trace_id=current_trace_id(),
            data=data,
        ),
    )


def publish_product_updated(
    broker: MessageBroker,
    product_id: uuid.UUID,
    changes: dict[str, Any],
) -> None:
    """Publish a ProductUpdated event.

    Call after a product update is successfully persisted. Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        product_id: UUID of the updated product.
        changes: Dict of field names to their new values.
    """
    _publish(
        broker,
        "catalog.product.updated",
        EventEnvelope(
            event_type="ProductUpdated",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="product",
            aggregate_id=str(product_id),
            trace_id=current_trace_id(),
            data=changes,
        ),
    )


def publish_product_deleted(
    broker: MessageBroker,
    product_id: uuid.UUID,
) -> None:
    """Publish a ProductDeleted event.

    Call after a product soft-delete is successfully persisted. Best-effort —
    failure logs a warning and does not affect the domain transaction.

    Args:
        broker: The message broker port.
        product_id: UUID of the deleted product.
    """
    _publish(
        broker,
        "catalog.product.deleted",
        EventEnvelope(
            event_type="ProductDeleted",
            version=_VERSION,
            producer=_DOMAIN,
            aggregate_type="product",
            aggregate_id=str(product_id),
            trace_id=current_trace_id(),
            data={"product_id": str(product_id)},
        ),
    )
