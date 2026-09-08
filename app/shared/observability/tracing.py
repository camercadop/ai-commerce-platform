import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

logger = logging.getLogger(__name__)


def configure_tracing(
    service_name: str,
    otlp_endpoint: str,
    enabled: bool = True,
) -> TracerProvider:
    """Configure OpenTelemetry tracing and return the active TracerProvider.

    When enabled, exports spans to the OTLP endpoint via gRPC using a
    BatchSpanProcessor. When disabled, uses an InMemorySpanExporter suitable
    for testing and local development without a collector.

    Call this once at application startup. Injects trace context into log
    records via LoggingInstrumentor so that every log line carries trace_id
    and span_id (ADR-005).

    Args:
        service_name: Identifies this service in traces (e.g. "catalog").
        otlp_endpoint: gRPC endpoint of the OTLP collector (e.g. "http://localhost:4317").
        enabled: When False, uses an in-memory exporter instead of OTLP.

    Returns:
        The configured TracerProvider set as the global tracer provider.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if enabled:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("Tracing enabled: exporting to %s", otlp_endpoint)
    else:
        provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
        logger.info("Tracing disabled: using in-memory exporter")

    trace.set_tracer_provider(provider)
    LoggingInstrumentor().instrument(set_logging_format=False)

    return provider
