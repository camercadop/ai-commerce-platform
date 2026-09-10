import logging
import uuid

from app.identity.models import Customer
from app.shared.events import EventEnvelope, MessageBroker
from app.shared.observability import current_trace_id

logger = logging.getLogger(__name__)

TOPIC = "identity.customer.registered"


def publish_customer_registered(broker: MessageBroker, customer: Customer) -> None:
    """Publish a CustomerRegistered event for the given customer.

    Called after a customer profile is successfully created. Consumers use
    this event to react to new registrations (e.g. send welcome emails,
    initialize loyalty accounts).

    Args:
        broker: The message broker to publish to.
        customer: The newly registered customer instance.
    """
    envelope = EventEnvelope(
        event_type="CustomerRegistered",
        version=1,
        producer="identity",
        aggregate_type="customer",
        aggregate_id=str(customer.id),
        trace_id=current_trace_id(),
        data={
            "customer_id": str(customer.id),
            "identity_provider_id": customer.identity_provider_id,
            "email": customer.email,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
        },
    )
    broker.publish(TOPIC, envelope)
    logger.info("Published %s for customer: %s", envelope.event_type, customer.id)


def make_customer_registered_envelope(customer_id: uuid.UUID) -> dict[str, str]:
    """Return the expected data payload shape for a CustomerRegistered event.

    Use this as a reference when writing consumers or tests that need to
    assert on the event payload structure.

    Args:
        customer_id: The UUID of the registered customer.
    """
    return {
        "customer_id": str(customer_id),
        "identity_provider_id": "<str>",
        "email": "<str>",
        "first_name": "<str>",
        "last_name": "<str>",
    }
