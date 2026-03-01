"""Tracing setup and Celery tracing signal integration."""

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
from opentelemetry.trace import ProxyTracerProvider

from django_o11y.config.setup import get_o11y_config
from django_o11y.logging.celery import setup_celery_logging
from django_o11y.logging.utils import get_logger
from django_o11y.tracing.fork import register_post_fork_handler
from django_o11y.tracing.instrumentation import setup_instrumentation
from django_o11y.tracing.utils import (
    is_celery_fork_pool_worker,
    is_celery_prefork_pool,
)
from django_o11y.utils.process import get_process_identity

logger = get_logger()

# Track instrumentation per-process to remain fork-safe.
_instrumented_pid: int | None = None
_tracing_initialized_pid: int | None = None


def setup_tracing(config: dict[str, Any]) -> Any:
    """Set up OpenTelemetry tracing provider and span processors."""
    global _tracing_initialized_pid

    service_name = config["SERVICE_NAME"]
    tracing_config = config["TRACING"]

    existing_provider = trace.get_tracer_provider()
    if not isinstance(existing_provider, ProxyTracerProvider):
        _tracing_initialized_pid = os.getpid()
        logger.debug(
            "Tracing provider already configured by %s.%s; skipping override [%s]",
            existing_provider.__class__.__module__,
            existing_provider.__class__.__name__,
            get_process_identity(),
        )
        return existing_provider

    instance_id = config.get("SERVICE_INSTANCE_ID") or (
        f"{os.getenv('HOSTNAME', socket.gethostname())}:{os.getpid()}"
    )

    resource_attrs = {
        SERVICE_NAME: service_name,
        SERVICE_VERSION: config["SERVICE_VERSION"],
        SERVICE_INSTANCE_ID: instance_id,
        "deployment.environment": config["ENVIRONMENT"],
        "host.name": socket.gethostname(),
        "process.pid": os.getpid(),
    }

    if config.get("NAMESPACE"):
        resource_attrs["service.namespace"] = config["NAMESPACE"]

    custom_attrs = config["RESOURCE_ATTRIBUTES"]
    if custom_attrs:
        resource_attrs.update(custom_attrs)

    resource = Resource(attributes=resource_attrs)
    sample_rate = tracing_config["SAMPLE_RATE"]
    sampler = ParentBased(root=TraceIdRatioBased(sample_rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    if tracing_config["OTLP_ENDPOINT"]:
        otlp_exporter = OTLPSpanExporter(
            endpoint=tracing_config["OTLP_ENDPOINT"], insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if tracing_config["CONSOLE_EXPORTER"]:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)
    _tracing_initialized_pid = os.getpid()
    logger.info(
        "Tracing configured for %s, sending to %s (%.0f%% sampling) [%s]",
        service_name,
        tracing_config["OTLP_ENDPOINT"],
        tracing_config["SAMPLE_RATE"] * 100,
        get_process_identity(),
    )

    _setup_pyroscope_correlation(provider, config)

    return provider


def _setup_pyroscope_correlation(
    provider: TracerProvider, config: dict[str, Any]
) -> None:
    """Attach Pyroscope span correlation when profiling is enabled."""
    if not config["PROFILING"].get("ENABLED"):
        return

    if is_celery_prefork_pool() and not is_celery_fork_pool_worker():
        logger.warning(
            "Skipping Pyroscope profile-trace correlation in Celery prefork "
            "parent process [%s]. Correlation is initialized in worker "
            "child processes post-fork.",
            get_process_identity(),
        )
        return

    try:
        from pyroscope.otel import PyroscopeSpanProcessor

        provider.add_span_processor(PyroscopeSpanProcessor())
        logger.info(
            "Pyroscope span processor added for profile-to-trace correlation [%s]",
            get_process_identity(),
        )
    except ImportError:
        logger.debug(
            "django_o11y: pyroscope-otel not installed, skipping profile-trace "
            "correlation. Install with: pip install django-o11y[profiling]"
        )


def setup_tracing_for_django(config: dict[str, Any]) -> None:
    """Configure tracing for Django startup in non-prefork parent processes."""
    if config.get("CELERY", {}).get("ENABLED", False):
        import importlib

        try:
            importlib.import_module("django_o11y.tracing.signals")
            _configure_celery_metrics_events(config)
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

    if _tracing_initialized_pid == os.getpid():
        return

    setup_instrumentation(config)
    setup_tracing(config)
    register_post_fork_handler()


def setup_celery_o11y(app: Any, config: dict[str, Any] | None = None) -> None:
    """Set up Celery worker logging and tracing bootstrap."""
    global _instrumented_pid

    if _instrumented_pid == os.getpid():
        return

    if config is None:
        config = get_o11y_config()

    celery_config = config.get("CELERY", {})
    if not celery_config.get("ENABLED", False):
        return

    setup_celery_logging(app)

    if config.get("TRACING", {}).get("ENABLED") and celery_config.get(
        "TRACING_ENABLED", True
    ):
        setup_instrumentation(config)
        setup_tracing(config)
        _setup_celery_tracing()

    _instrumented_pid = os.getpid()


def setup_worker_metrics(celery_config: dict[str, Any]) -> None:
    """Start the Prometheus metrics HTTP server in the Celery parent process.

    Must be called in the prefork **parent** process (``worker_init``) so that:
    - ``PROMETHEUS_MULTIPROC_DIR`` is already set in the environment (by the
      operator's entrypoint) before this runs.
    - The HTTP server is only bound once (in the parent).
    - Child processes inherit ``PROMETHEUS_MULTIPROC_DIR`` via fork.

    ``PROMETHEUS_MULTIPROC_DIR`` must be pre-created by the process entrypoint.
    django-o11y does not create it.
    """
    import pathlib

    from prometheus_client import CollectorRegistry, start_http_server
    from prometheus_client.multiprocess import MultiProcessCollector

    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not multiproc_dir:
        logger.warning(
            "PROMETHEUS_MULTIPROC_DIR is not set; "
            "Celery worker metrics server will not be started."
        )
        return

    # Clear stale files from previous runs. In multiprocess mode these files
    # are append-only snapshots; keeping old ones causes stale metrics.
    multiproc_path = pathlib.Path(multiproc_dir)
    for db_file in multiproc_path.glob("*.db"):
        db_file.unlink(missing_ok=True)

    port = celery_config["METRICS_PORT"]
    registry = CollectorRegistry()
    MultiProcessCollector(registry)
    start_http_server(port, registry=registry)
    logger.info(
        "Celery worker metrics server started on port %d (multiproc dir: %s)",
        port,
        multiproc_dir,
    )


def _configure_celery_metrics_events(config: dict[str, Any]) -> None:
    """Set Celery event flags needed by celery-exporter on the app conf at startup.

    Setting these on the app conf before the worker boots means the worker
    reads the correct values during its own startup sequence, avoiding the
    ``task events: OFF`` banner.
    """
    celery_config = config.get("CELERY", {})
    if not config.get("METRICS", {}).get("PROMETHEUS_ENABLED", True):
        return
    if not celery_config.get("METRICS_ENABLED", True):
        return

    try:
        import celery as celery_module

        app = celery_module.current_app
        app.conf.worker_send_task_events = True
        app.conf.task_send_sent_event = True
    except Exception:  # pragma: no cover
        logger.debug(
            "Failed to enable Celery task events in Django/worker process",
            exc_info=True,
        )


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
