from app.shared.config import AppSettings


class ObservabilitySettings(AppSettings):
    """Configuration for OpenTelemetry tracing and structured logging.

    All values are validated at startup. A missing or invalid value causes
    the application to fail before serving any traffic (ADR-015).
    """

    otel_service_name: str
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_enabled: bool = True
