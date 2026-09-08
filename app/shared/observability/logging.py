import logging

_LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "trace_id=%(otelTraceID)s span_id=%(otelSpanID)s %(message)s"
)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structured logging with OpenTelemetry trace correlation.

    Call this once at application startup before any domain loggers emit output.
    Injects trace_id and span_id into every log record so that logs can be
    correlated with traces (ADR-005).

    Args:
        level: The root log level. Defaults to INFO.
    """
    logging.basicConfig(level=level, format=_LOG_FORMAT)
