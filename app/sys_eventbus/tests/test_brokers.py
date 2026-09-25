import json
from unittest.mock import MagicMock, patch

import pytest

from app.shared.events.envelope import EventEnvelope
from app.sys_eventbus.brokers import KafkaMessageBroker


@pytest.fixture()
def envelope() -> EventEnvelope:
    return EventEnvelope(
        event_type="ProductCreated",
        version=1,
        producer="catalog",
        aggregate_type="product",
        aggregate_id="prod-1",
        trace_id="trace-abc",
        data={"id": "prod-1"},
    )


@pytest.fixture()
def broker() -> KafkaMessageBroker:
    return KafkaMessageBroker(bootstrap_servers="localhost:9092", group_id="test-group")


# ---------------------------------------------------------------------------
# KafkaMessageBroker
# ---------------------------------------------------------------------------


class TestKafkaMessageBrokerPublish:
    def test_raises_if_not_started(
        self, broker: KafkaMessageBroker, envelope: EventEnvelope
    ) -> None:
        with pytest.raises(RuntimeError, match="not been started"):
            broker.publish("catalog.product.created", envelope)

    def test_serializes_envelope_to_json_utf8(
        self, broker: KafkaMessageBroker, envelope: EventEnvelope
    ) -> None:
        mock_producer = MagicMock()
        broker._producer = mock_producer

        broker.publish("catalog.product.created", envelope)

        mock_producer.produce.assert_called_once()
        topic, value = mock_producer.produce.call_args[0]
        assert topic == "catalog.product.created"
        assert isinstance(value, bytes)
        parsed = json.loads(value.decode("utf-8"))
        assert parsed["event_type"] == "ProductCreated"
        assert parsed["aggregate_id"] == "prod-1"

    def test_polls_after_produce(
        self, broker: KafkaMessageBroker, envelope: EventEnvelope
    ) -> None:
        mock_producer = MagicMock()
        broker._producer = mock_producer

        broker.publish("catalog.product.created", envelope)

        mock_producer.poll.assert_called_once_with(0)


class TestKafkaMessageBrokerSubscribe:
    def test_registers_handler(self, broker: KafkaMessageBroker) -> None:
        handler = MagicMock()

        broker.subscribe("catalog.product.created", handler)

        assert broker._handlers["catalog.product.created"] is handler

    def test_overwrites_existing_handler(self, broker: KafkaMessageBroker) -> None:
        first = MagicMock()
        second = MagicMock()

        broker.subscribe("catalog.product.created", first)
        broker.subscribe("catalog.product.created", second)

        assert broker._handlers["catalog.product.created"] is second


class TestKafkaMessageBrokerLifecycle:
    def test_start_creates_producer_and_consumer(
        self, broker: KafkaMessageBroker
    ) -> None:
        with (
            patch("app.sys_eventbus.brokers.Producer") as mock_producer_cls,
            patch("app.sys_eventbus.brokers.Consumer") as mock_consumer_cls,
            patch("app.sys_eventbus.brokers.threading.Thread") as mock_thread_cls,
        ):
            mock_thread_cls.return_value = MagicMock()
            broker.start()

        mock_producer_cls.assert_called_once()
        mock_consumer_cls.assert_called_once()

    def test_start_launches_consumer_thread(
        self, broker: KafkaMessageBroker
    ) -> None:
        with (
            patch("app.sys_eventbus.brokers.Producer"),
            patch("app.sys_eventbus.brokers.Consumer"),
            patch("app.sys_eventbus.brokers.threading.Thread") as mock_thread_cls,
        ):
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            broker.start()

        mock_thread.start.assert_called_once()

    def test_stop_signals_thread_and_flushes(
        self, broker: KafkaMessageBroker
    ) -> None:
        mock_producer = MagicMock()
        mock_consumer = MagicMock()
        mock_thread = MagicMock()
        mock_stop_event = MagicMock()

        broker._producer = mock_producer
        broker._consumer = mock_consumer
        broker._consumer_thread = mock_thread
        broker._stop_event = mock_stop_event

        broker.stop()

        mock_stop_event.set.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5.0)
        mock_consumer.close.assert_called_once()
        mock_producer.flush.assert_called_once()
