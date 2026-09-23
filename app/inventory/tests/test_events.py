import uuid
from unittest.mock import MagicMock

from app.inventory.events import (
    publish_inventory_reserved,
    publish_inventory_released,
    publish_inventory_confirmed,
)
from app.shared.events import EventEnvelope


class TestPublishInventoryReserved:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        reservation_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()

        publish_inventory_reserved(
            broker, reservation_id, variant_id, order_id, 3
        )

        broker.publish.assert_called_once()
        topic, _ = broker.publish.call_args.args
        assert topic == "inventory.stock.reserved"

    def test_envelope_contains_reservation_data(self) -> None:
        broker = MagicMock()
        reservation_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()

        publish_inventory_reserved(
            broker, reservation_id, variant_id, order_id, 3
        )

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "InventoryReserved"
        assert envelope.version == 1
        assert envelope.producer == "inventory"
        assert envelope.aggregate_type == "inventory_item"
        assert envelope.aggregate_id == str(variant_id)
        assert envelope.data["reservation_id"] == str(reservation_id)
        assert envelope.data["variant_id"] == str(variant_id)
        assert envelope.data["order_id"] == str(order_id)
        assert envelope.data["quantity"] == 3

    def test_swallows_broker_exception(self) -> None:
        broker = MagicMock()
        broker.publish.side_effect = RuntimeError("broker down")

        publish_inventory_reserved(
            broker, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), 3
        )


class TestPublishInventoryReleased:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        reservation_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()

        publish_inventory_released(
            broker, reservation_id, variant_id, order_id, 3
        )

        broker.publish.assert_called_once()
        topic, _ = broker.publish.call_args.args
        assert topic == "inventory.stock.released"

    def test_envelope_contains_reservation_data(self) -> None:
        broker = MagicMock()
        reservation_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()

        publish_inventory_released(
            broker, reservation_id, variant_id, order_id, 3
        )

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "InventoryReleased"
        assert envelope.version == 1
        assert envelope.producer == "inventory"
        assert envelope.aggregate_type == "inventory_item"
        assert envelope.aggregate_id == str(variant_id)
        assert envelope.data["reservation_id"] == str(reservation_id)
        assert envelope.data["variant_id"] == str(variant_id)
        assert envelope.data["order_id"] == str(order_id)
        assert envelope.data["quantity"] == 3

    def test_swallows_broker_exception(self) -> None:
        broker = MagicMock()
        broker.publish.side_effect = RuntimeError("broker down")

        publish_inventory_released(
            broker, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), 3
        )


class TestPublishInventoryConfirmed:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        reservation_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()

        publish_inventory_confirmed(
            broker, reservation_id, variant_id, order_id, 3
        )

        broker.publish.assert_called_once()
        topic, _ = broker.publish.call_args.args
        assert topic == "inventory.stock.confirmed"

    def test_envelope_contains_reservation_data(self) -> None:
        broker = MagicMock()
        reservation_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()

        publish_inventory_confirmed(
            broker, reservation_id, variant_id, order_id, 3
        )

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "InventoryConfirmed"
        assert envelope.version == 1
        assert envelope.producer == "inventory"
        assert envelope.aggregate_type == "inventory_item"
        assert envelope.aggregate_id == str(variant_id)
        assert envelope.data["reservation_id"] == str(reservation_id)
        assert envelope.data["variant_id"] == str(variant_id)
        assert envelope.data["order_id"] == str(order_id)
        assert envelope.data["quantity"] == 3

    def test_swallows_broker_exception(self) -> None:
        broker = MagicMock()
        broker.publish.side_effect = RuntimeError("broker down")

        publish_inventory_confirmed(
            broker, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), 3
        )
