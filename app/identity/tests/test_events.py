from unittest.mock import MagicMock

from app.identity.events import TOPIC, publish_customer_registered
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
