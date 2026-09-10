from unittest.mock import MagicMock

from app.identity.events import (
    TOPIC,
    make_customer_registered_envelope,
    publish_customer_registered,
)
from app.identity.tests.fakes import make_customer
from app.shared.events import EventEnvelope


class TestPublishCustomerRegistered:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        customer = make_customer()

        publish_customer_registered(broker, customer)

        broker.publish.assert_called_once()
        topic, envelope = broker.publish.call_args.args
        assert topic == TOPIC

    def test_envelope_contains_customer_data(self) -> None:
        broker = MagicMock()
        customer = make_customer(
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        publish_customer_registered(broker, customer)

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "CustomerRegistered"
        assert envelope.version == 1
        assert envelope.producer == "identity"
        assert envelope.aggregate_type == "customer"
        assert envelope.aggregate_id == str(customer.id)
        assert envelope.data["email"] == "jane@example.com"
        assert envelope.data["first_name"] == "Jane"


class TestMakeCustomerRegisteredEnvelope:
    def test_returns_payload_with_customer_id(self) -> None:
        import uuid

        customer_id = uuid.uuid4()

        payload = make_customer_registered_envelope(customer_id)

        assert payload["customer_id"] == str(customer_id)
        assert set(payload.keys()) == {
            "customer_id",
            "identity_provider_id",
            "email",
            "first_name",
            "last_name",
        }
