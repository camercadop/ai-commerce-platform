from app.shared.config import AppSettings


class KafkaSettings(AppSettings):
    """Kafka message broker configuration.

    The Kafka bootstrap servers are required when the message broker is
    enabled. A missing value causes the application to fail before serving
    any traffic (ADR-015).
    """

    kafka_bootstrap_servers: str
