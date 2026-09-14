import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from app.catalog.events import (
    publish_product_created,
    publish_product_deleted,
    publish_product_updated,
)
from app.shared.events import EventEnvelope


class TestPublishProductCreated:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        product_id = uuid.uuid4()

        publish_product_created(
            broker, product_id, sku="SKU-1", name="Widget", base_price=Decimal("9.99"), status="draft"
        )

        broker.publish.assert_called_once()
        topic, _ = broker.publish.call_args.args
        assert topic == "catalog.product.created"

    def test_envelope_contains_product_data(self) -> None:
        broker = MagicMock()
        product_id = uuid.uuid4()

        publish_product_created(
            broker, product_id, sku="SKU-1", name="Widget", base_price=Decimal("9.99"), status="draft"
        )

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "ProductCreated"
        assert envelope.version == 1
        assert envelope.producer == "catalog"
        assert envelope.aggregate_type == "product"
        assert envelope.aggregate_id == str(product_id)
        assert envelope.data["sku"] == "SKU-1"
        assert envelope.data["name"] == "Widget"
        assert envelope.data["base_price"] == "9.99"
        assert envelope.data["status"] == "draft"

    def test_optional_fields_default_to_none(self) -> None:
        broker = MagicMock()

        publish_product_created(
            broker, uuid.uuid4(), sku="SKU-1", name="Widget", base_price=Decimal("9.99"), status="draft"
        )

        _, envelope = broker.publish.call_args.args
        assert envelope.data["category_id"] is None
        assert envelope.data["brand_id"] is None
        assert envelope.data["description"] is None
        assert envelope.data["specs"] is None

    def test_optional_fields_serialized_when_provided(self) -> None:
        broker = MagicMock()
        category_id = uuid.uuid4()
        brand_id = uuid.uuid4()

        publish_product_created(
            broker,
            uuid.uuid4(),
            sku="SKU-1",
            name="Widget",
            base_price=Decimal("9.99"),
            status="active",
            category_id=category_id,
            brand_id=brand_id,
            description="A widget",
            specs={"material": "plastic"},
        )

        _, envelope = broker.publish.call_args.args
        assert envelope.data["category_id"] == str(category_id)
        assert envelope.data["brand_id"] == str(brand_id)
        assert envelope.data["description"] == "A widget"
        assert envelope.data["specs"] == {"material": "plastic"}

    def test_swallows_broker_exception(self) -> None:
        broker = MagicMock()
        broker.publish.side_effect = RuntimeError("broker down")

        publish_product_created(
            broker, uuid.uuid4(), sku="SKU-1", name="Widget", base_price=Decimal("9.99"), status="draft"
        )


class TestPublishProductUpdated:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        product_id = uuid.uuid4()

        publish_product_updated(broker, product_id, changes={"name": "New Name"})

        broker.publish.assert_called_once()
        topic, _ = broker.publish.call_args.args
        assert topic == "catalog.product.updated"

    def test_envelope_contains_changes(self) -> None:
        broker = MagicMock()
        product_id = uuid.uuid4()

        publish_product_updated(broker, product_id, changes={"name": "New Name"})

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "ProductUpdated"
        assert envelope.aggregate_id == str(product_id)
        assert envelope.data == {"name": "New Name"}

    def test_swallows_broker_exception(self) -> None:
        broker = MagicMock()
        broker.publish.side_effect = RuntimeError("broker down")

        publish_product_updated(broker, uuid.uuid4(), changes={"name": "x"})


class TestPublishProductDeleted:
    def test_publishes_to_correct_topic(self) -> None:
        broker = MagicMock()
        product_id = uuid.uuid4()

        publish_product_deleted(broker, product_id)

        broker.publish.assert_called_once()
        topic, _ = broker.publish.call_args.args
        assert topic == "catalog.product.deleted"

    def test_envelope_contains_product_id(self) -> None:
        broker = MagicMock()
        product_id = uuid.uuid4()

        publish_product_deleted(broker, product_id)

        _, envelope = broker.publish.call_args.args
        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "ProductDeleted"
        assert envelope.aggregate_id == str(product_id)
        assert envelope.data == {"product_id": str(product_id)}

    def test_swallows_broker_exception(self) -> None:
        broker = MagicMock()
        broker.publish.side_effect = RuntimeError("broker down")

        publish_product_deleted(broker, uuid.uuid4())
