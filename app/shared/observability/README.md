# observability

Provides structured logging and OpenTelemetry tracing setup. Both must be initialized
once at application startup. Log records are automatically correlated with the active
trace via injected `trace_id` and `span_id` fields (ADR-005).

## Package layout

```
observability/
├── __init__.py     # Package entry point
├── logging.py      # Structured logging setup
├── settings.py     # Observability configuration
└── tracing.py      # OpenTelemetry tracing setup
```

## Public API

| Symbol | Description |
| --- | --- |
| `configure_logging(level)` | Configures the root logger with OTel-correlated structured format |
| `configure_tracing(service_name, otlp_endpoint, enabled)` | Sets up the global `TracerProvider`; exports via OTLP gRPC when `enabled=True` |
| `current_trace_id()` | Returns the active OTel trace ID as a 32-char hex string, or `""` if no active span |
| `ObservabilitySettings` | `AppSettings` subclass for service name, OTLP endpoint, and enabled flag |

`configure_tracing()` with `enabled=False` uses an `InMemorySpanExporter` — suitable
for tests and local development without a collector.

Use `current_trace_id()` anywhere a trace context must be propagated, such as event
envelopes and audit records.

```python
from app.shared.observability import (
    configure_logging,
    configure_tracing,
    current_trace_id,
)

# call both once at application startup
configure_logging()
configure_tracing(
    service_name=settings.otel_service_name,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    enabled=settings.otel_enabled,
)

# propagate trace context in events or audit records
trace_id = current_trace_id()  # "4bf92f3577b34da6a3ce929d0e0e4736" or ""
```

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `OTEL_SERVICE_NAME` | Service name reported in traces | required |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | gRPC endpoint of the OTLP collector | `http://localhost:4317` |
| `OTEL_ENABLED` | When `False`, uses in-memory exporter instead of OTLP | `True` |
