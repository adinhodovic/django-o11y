"""Logging helpers."""

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


# GCP Cloud Logging numeric severity values.
# https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#logseverity
_SEVERITY_LEVELS: dict[str, int] = {
    "debug": 100,
    "info": 200,
    "warning": 400,
    "error": 500,
    "critical": 600,
}


def add_severity(_: Any, __: Any, event_dict: dict) -> dict:
    """Inject a GCP-compatible numeric ``severity`` field into log events."""
    level = event_dict.get("level", "")
    event_dict["severity"] = _SEVERITY_LEVELS.get(level.lower(), 0)
    return event_dict


def get_logger() -> structlog.BoundLoggerBase:
    """Return a structlog logger bound to the caller module name."""
    frame = sys._getframe(1)
    name: str = frame.f_globals.get("__name__", __name__)
    return structlog.get_logger(name)


def add_log_context(**kwargs: Any) -> None:
    """Add key-value pairs to structlog context only (not traces)."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_custom_context() -> None:
    """Clear all structlog context variables."""
    structlog.contextvars.clear_contextvars()


def add_open_telemetry_spans(_: Any, __: Any, event_dict: dict) -> dict:
    """Attach current OpenTelemetry span ids to log events."""
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span_id"] = f"{ctx.span_id:x}"
    event_dict["trace_id"] = f"{ctx.trace_id:x}"
    if parent:
        event_dict["parent_span_id"] = f"{parent.span_id:x}"

    return event_dict


class OTLPHandler(LoggingHandler):
    """Logging handler that exports logs to an OTLP endpoint."""

    def __init__(self, endpoint: str, service_name: str = "django-app", **kwargs: Any):
        resource = Resource(attributes={SERVICE_NAME: service_name})
        logger_provider = LoggerProvider(resource=resource)

        otlp_exporter = OTLPLogExporter(endpoint=endpoint, insecure=True)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

        set_logger_provider(logger_provider)
        super().__init__(level=logging.NOTSET, logger_provider=logger_provider)
