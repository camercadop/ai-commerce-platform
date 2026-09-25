import json
import logging
import threading
from collections.abc import Callable

from confluent_kafka import Consumer, Producer

from app.shared.events.broker import MessageBroker
from app.shared.events.envelope import EventEnvelope

logger = logging.getLogger(__name__)


class KafkaMessageBroker(MessageBroker):
    """Kafka-backed message broker implementation.

    Uses the `confluent-kafka` library to publish and consume domain events.
    Each event envelope is serialized as a JSON UTF-8 message value and
    published to the Kafka topic named by the topic argument.
    """

    def __init__(
        self, bootstrap_servers: str, group_id: str = "commerce-platform"
    ) -> None:
        """Initialize the Kafka message broker.

        Args:
            bootstrap_servers: Kafka bootstrap servers (e.g. "localhost:9092").
            group_id: Consumer group identifier (default "commerce-platform").
        """
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._producer: Producer | None = None
        self._consumer: Consumer | None = None
        self._handlers: dict[str, Callable[[EventEnvelope], None]] = {}
        self._consumer_thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

    def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Publish an event envelope to the given topic.

        The envelope is serialized to JSON (UTF-8) and published to the
        Kafka topic named by the topic argument.

        Args:
            topic: The Kafka topic to publish to.
            envelope: The fully constructed event envelope.
        """
        if self._producer is None:
            raise RuntimeError("KafkaMessageBroker has not been started yet")

        value = json.dumps(envelope.model_dump(mode="json"), ensure_ascii=False).encode(
            "utf-8"
        )
        self._producer.produce(topic, value)
        self._producer.poll(0)

    def subscribe(self, topic: str, handler: Callable[[EventEnvelope], None]) -> None:
        """Register a handler to be called for each event on the given topic.

        Handlers are invoked from a background consumer thread.

        Args:
            topic: The Kafka topic to subscribe to.
            handler: Callable that receives a deserialized EventEnvelope.
        """
        self._handlers[topic] = handler

    def start(self) -> None:
        """Start the broker and begin any background consumer loops.

        Creates the Kafka producer and consumer, then launches the consumer
        loop in a background thread.
        """
        self._producer = Producer(
            {"bootstrap.servers": self._bootstrap_servers},
        )
        self._consumer = Consumer(
            {
                "bootstrap.servers": self._bootstrap_servers,
                "group.id": self._group_id,
                "auto.offset.reset": "earliest",
            },
        )
        self._stop_event = threading.Event()
        self._consumer_thread = threading.Thread(
            target=self._consumer_loop, daemon=True
        )
        self._consumer_thread.start()

    def stop(self) -> None:
        """Stop the broker and drain any background consumer loops.

        Signals the consumer thread to exit and waits for it to finish.
        """
        if self._stop_event:
            self._stop_event.set()
        if self._consumer_thread:
            self._consumer_thread.join(timeout=5.0)
        if self._consumer:
            self._consumer.close()
        if self._producer:
            self._producer.flush()

    def _consumer_loop(self) -> None:
        """Background consumer loop.

        Subscribes to all registered topics and invokes handlers for each
        received message.
        """
        if self._consumer is None or self._stop_event is None:
            return
        self._consumer.subscribe(list(self._handlers.keys()))
        while not self._stop_event.is_set():
            msg = self._consumer.poll(0.1)
            if msg is None:
                continue
            if msg.error():
                logger.error("Kafka consumer error: %s", msg.error())
                continue
            topic = msg.topic()
            handler = self._handlers.get(topic) if topic else None
            if handler:
                try:
                    raw_value = msg.value()
                    if raw_value is None:
                        continue
                    envelope = EventEnvelope.model_validate_json(raw_value)
                    handler(envelope)
                except Exception:
                    logger.exception("Error handling message on topic %s", msg.topic())
