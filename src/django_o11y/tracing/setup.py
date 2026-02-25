"""Tracing setup and Celery tracing signal integration."""

import logging
import multiprocessing
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
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from django_o11y.config.setup import get_o11y_config
from django_o11y.logging.utils import get_logger
from django_o11y.tracing.fork import register_post_fork_handler
from django_o11y.tracing.instrumentation import setup_instrumentation
from django_o11y.tracing.utils import (
    is_celery_fork_pool_worker,
    is_celery_prefork_pool,
)

logger = get_logger()
provider_logger = logging.getLogger("django_o11y.tracing")

# Track instrumentation per-process to remain fork-safe.
_instrumented_pid: int | None = None


def _process_identity() -> str:
    """Return process identity details for startup diagnostics."""
    return (
        f"pid={os.getpid()} ppid={os.getppid()} "
        f"process={multiprocessing.current_process().name}"
    )


def setup_tracing(config: dict[str, Any]) -> TracerProvider:
    """Set up OpenTelemetry tracing provider and span processors."""
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
    sample_rate = tracing_config.get("SAMPLE_RATE", 1.0)
    sampler = ParentBased(root=TraceIdRatioBased(sample_rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    if tracing_config["OTLP_ENDPOINT"]:
        otlp_exporter = OTLPSpanExporter(
            endpoint=tracing_config["OTLP_ENDPOINT"], insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if tracing_config.get("CONSOLE_EXPORTER", False):
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)
    provider_logger.info(
        "Tracing configured for %s, sending to %s (%.0f%% sampling) [%s]",
        service_name,
        tracing_config["OTLP_ENDPOINT"],
        tracing_config.get("SAMPLE_RATE", 1.0) * 100,
        _process_identity(),
    )

    profiling_config = config.get("PROFILING", {})
    if profiling_config.get("ENABLED"):
        is_prefork_parent = (
            is_celery_prefork_pool() and not is_celery_fork_pool_worker()
        )
        if is_prefork_parent:
            provider_logger.warning(
                "Skipping Pyroscope profile-trace correlation in Celery prefork "
                "parent process [%s]. Correlation is initialized in worker "
                "child processes post-fork.",
                _process_identity(),
            )
            return provider

        try:
            from pyroscope.otel import PyroscopeSpanProcessor

            provider.add_span_processor(PyroscopeSpanProcessor())
            provider_logger.info(
                "Pyroscope span processor added for profile-to-trace correlation"
            )
        except ImportError:
            provider_logger.debug(
                "django_o11y: pyroscope-otel not installed, skipping profile-trace "
                "correlation. Install with: pip install django-o11y[profiling]"
            )

    return provider


def setup_tracing_for_django(config: dict[str, Any]) -> None:
    """Configure tracing for Django startup in non-prefork parent processes."""
    if config.get("CELERY", {}).get("ENABLED", False):
        import importlib

        try:
            importlib.import_module("django_o11y.tracing.signals")
        except ImportError:
            logger.warning(
                "CELERY.ENABLED is true but Celery is not installed. "
                "Install with: pip install django-o11y[celery]"
            )

    if not config.get("TRACING", {}).get("ENABLED", False):
        logger.info("Tracing disabled")
        return

    if is_celery_prefork_pool():
        logger.info(
            "Skipping tracing setup in Celery prefork parent; "
            "child workers initialize tracing post-fork"
        )
        return

    setup_instrumentation(config)
    setup_tracing(config)
    register_post_fork_handler()


def setup_celery_o11y(app: Any, config: dict[str, Any] | None = None) -> None:
    """Set up tracing and worker defaults for Celery tasks."""
    global _instrumented_pid

    if _instrumented_pid == os.getpid():
        return

    if config is None:
        config = get_o11y_config()

    celery_config = config.get("CELERY", {})
    if not celery_config.get("ENABLED", False):
        return

    # Keep Django/structlog logging ownership in workers.
    app.conf.worker_hijack_root_logger = False
    app.conf.worker_redirect_stdouts = False
    app.conf.worker_send_task_events = True
    app.conf.task_send_sent_event = True

    from django_structlog.celery.steps import DjangoStructLogInitStep

    app.steps["worker"].add(DjangoStructLogInitStep)

    if config.get("TRACING", {}).get("ENABLED") and celery_config.get(
        "TRACING_ENABLED", True
    ):
        setup_tracing(config)
        _setup_celery_tracing()

    _instrumented_pid = os.getpid()


def _setup_celery_tracing() -> None:
    """Set up automatic tracing for Celery tasks."""
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        instrumentor = CeleryInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
    except ImportError:
        logger.warning(
            "Celery tracing is enabled but 'opentelemetry-instrumentation-celery' "
            "is not installed. "
            "Install it with: pip install opentelemetry-instrumentation-celery"
        )
