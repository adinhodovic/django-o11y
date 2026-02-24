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

logger = logging.getLogger("django_o11y.tracing")


def _is_celery_fork_pool_worker() -> bool:
    """Return True when running inside a Celery prefork pool child."""
    from django_o11y.celery.detection import is_celery_fork_pool_worker

    return is_celery_fork_pool_worker()


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
        if _is_celery_fork_pool_worker():
            # Disabled in Celery prefork workers due to known native instability.
            # Context: https://github.com/grafana/pyroscope-rs/issues/276
            logger.warning(
                "Skipping Pyroscope profile-trace correlation in Celery prefork "
                "worker; this avoids pyroscope-io fork instability"
            )
            return provider

        try:
            from pyroscope.otel import PyroscopeSpanProcessor

            provider.add_span_processor(PyroscopeSpanProcessor())
            logger.info(
                "Pyroscope span processor added for profile-to-trace correlation"
            )
        except ImportError:
            logger.debug(
                "django_o11y: pyroscope-otel not installed, skipping profile-trace "
                "correlation. Install with: pip install django-o11y[profiling]"
            )

    return provider
