"""OpenTelemetry tracing provider setup."""

import logging
import os
import socket
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import (
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
    SERVICE_VERSION,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from django_o11y.tracing.pyroscope import build_pyroscope_span_processor

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

    # SERVICE_INSTANCE_ID: use the explicit value from config/env if set,
    # otherwise compute hostname:pid fresh at call time.  Calling os.getpid()
    # here (rather than reading a cached config value) means forked workers
    # automatically get their own pid after _reinit_after_fork() calls us.
    instance_id = config.get("SERVICE_INSTANCE_ID") or (
        f"{os.getenv('HOSTNAME', socket.gethostname())}:{os.getpid()}"
    )

    resource_attrs = {
        SERVICE_NAME: service_name,
        SERVICE_VERSION: config.get("SERVICE_VERSION", "unknown"),
        SERVICE_INSTANCE_ID: instance_id,
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

    profiling_config = config.get("PROFILING", {})
    if profiling_config.get("ENABLED"):
        pyroscope_span_processor = build_pyroscope_span_processor()
        if pyroscope_span_processor is not None:
            provider.add_span_processor(pyroscope_span_processor)
            logger.info(
                "Pyroscope span processor added for profile-to-trace correlation"
            )
        else:
            logger.debug(
                "django_o11y: pyroscope-io not installed, skipping profile-trace "
                "correlation. Install with: pip install django-o11y[profiling]"
            )

    return provider
