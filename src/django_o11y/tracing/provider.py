"""OpenTelemetry tracing provider setup."""

import logging
import os
import socket
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from django_o11y import __version__

logger = logging.getLogger("django_o11y.tracing")


def setup_tracing(config: dict[str, Any]) -> TracerProvider:
    """
    Set up OpenTelemetry tracing.

    Args:
        config: Configuration dictionary from get_o11y_config()

    Returns:
        TracerProvider instance
    """
    service_name = config["SERVICE_NAME"]
    tracing_config = config["TRACING"]

    resource_attrs = {
        SERVICE_NAME: service_name,
        "service.version": os.getenv("SERVICE_VERSION", __version__),
        "deployment.environment": config.get("ENVIRONMENT", "development"),
        "host.name": socket.gethostname(),
        "process.pid": os.getpid(),
    }

    if config.get("NAMESPACE"):
        resource_attrs["service.namespace"] = config["NAMESPACE"]

    custom_attrs = config.get("RESOURCE_ATTRIBUTES", {})
    if custom_attrs:
        resource_attrs.update(custom_attrs)

    resource = Resource(attributes=resource_attrs)
    provider = TracerProvider(resource=resource)

    if tracing_config["OTLP_ENDPOINT"]:
        otlp_exporter = OTLPSpanExporter(
            endpoint=tracing_config["OTLP_ENDPOINT"], insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if tracing_config.get("CONSOLE_EXPORTER", False):
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)
    logger.info(
        "Tracing configured for %s, sending to %s (%.0f%% sampling)",
        service_name,
        tracing_config["OTLP_ENDPOINT"],
        tracing_config.get("SAMPLE_RATE", 1.0) * 100,
    )
    return provider
