import os

from app.shared.events import MessageBroker, NoOpMessageBroker
from app.sys_eventbus.brokers import KafkaMessageBroker


def resolve_broker(group_id: str = "commerce-platform") -> MessageBroker:
    """Return a configured MessageBroker based on the environment.

    Instantiates a KafkaMessageBroker when KAFKA_BOOTSTRAP_SERVERS is set;
    falls back to NoOpMessageBroker otherwise.

    Args:
        group_id: Consumer group id passed to KafkaMessageBroker.

    Returns:
        A ready-to-start MessageBroker instance.
    """
    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
    if bootstrap_servers:
        return KafkaMessageBroker(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
        )
    return NoOpMessageBroker()
