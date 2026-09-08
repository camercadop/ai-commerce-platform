import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import ValidationError

from app.shared.observability import (
    ObservabilitySettings,
    configure_logging,
    configure_tracing,
)


def test_observability_settings_fails_without_service_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    with pytest.raises(ValidationError):
        ObservabilitySettings()


def test_observability_settings_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SERVICE_NAME", "catalog")

    settings = ObservabilitySettings()

    assert settings.otel_service_name == "catalog"
    assert settings.otel_exporter_otlp_endpoint == "http://localhost:4317"
    assert settings.otel_enabled is True


def test_configure_logging_sets_root_level() -> None:
    configure_logging(level=logging.WARNING)

    assert logging.getLogger().level == logging.WARNING


def test_configure_tracing_disabled_uses_in_memory_exporter() -> None:
    provider = configure_tracing(
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        enabled=False,
    )

    assert isinstance(provider, TracerProvider)


def test_configure_tracing_returns_tracer_provider() -> None:
    provider = configure_tracing(
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        enabled=False,
    )

    assert isinstance(provider, TracerProvider)


def test_configure_tracing_produces_spans() -> None:
    exporter = InMemorySpanExporter()
    provider = configure_tracing(
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        enabled=False,
    )
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider.add_span_processor(SimpleSpanProcessor(exporter))

    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("test-span"):
        pass

    spans = exporter.get_finished_spans()
    assert any(s.name == "test-span" for s in spans)
