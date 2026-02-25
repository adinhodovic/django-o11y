"""Setup module for Celery o11y integration."""

import os
from typing import Any

from celery.signals import (
    setup_logging,
    worker_init,
    worker_process_init,
    worker_process_shutdown,
)

from django_o11y.celery.detection import (
    is_celery_fork_pool_worker,
    is_celery_prefork_pool,
)
from django_o11y.conf import get_o11y_config
from django_o11y.context import get_logger
from django_o11y.profiling import setup_profiling
from django_o11y.tracing.provider import setup_tracing

# Track instrumentation per-process to remain fork-safe.
_instrumented_pid: int | None = None
logger = get_logger()


def _connect(signal, dispatch_uid: str):
    """Return a decorator that registers handler when Celery is available."""

    def _decorator(func):
        signal.connect(func, weak=False, dispatch_uid=dispatch_uid)
        return func

    return _decorator


def _maybe_force_flush(config: dict[str, Any], reason: str) -> None:
    """Flush pending spans from current process provider."""
    if not config.get("TRACING", {}).get("ENABLED", False):
        return

    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        force_flush = getattr(provider, "force_flush", None)
        if callable(force_flush):
            force_flush()
    except Exception:  # pragma: no cover
        logger.warning(
            "Failed to force-flush tracer provider on %s", reason, exc_info=True
        )


def setup_celery_o11y(app: Any, config: dict[str, Any] | None = None) -> None:
    """
    Set up tracing, logging, and metrics for Celery tasks.

    Called automatically on worker start when ``CELERY.ENABLED`` is True.
    Can also be called manually for explicit control.
    """
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


@_connect(setup_logging, dispatch_uid="django_o11y.celery.setup_logging")
def _config_loggers(*args, **kwargs):  # pylint: disable=unused-variable
    """Use Django's LOGGING config for Celery worker logging setup."""
    import logging.config as _logging_config

    from django.conf import settings

    if hasattr(settings, "LOGGING") and settings.LOGGING:
        _logging_config.dictConfig(settings.LOGGING)
        # Returning truthy tells Celery to skip its own logger setup.
        return True
    return False


def _setup_celery_tracing() -> None:
    """Set up automatic tracing for Celery tasks.

    In prefork mode, monkey-patches are inherited across fork. We only need to
    ensure instrumentation is applied once per process to avoid OTel warnings.
    """
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


@_connect(worker_init, dispatch_uid="django_o11y.celery.worker_init")
def _auto_setup_on_worker_init(sender, **kwargs) -> None:
    """worker_init signal handler — runs setup_celery_o11y on worker start."""
    if is_celery_prefork_pool():
        return

    _auto_setup_worker(sender, prefork=False)


def _resolve_worker_app(sender):
    """Resolve Celery app from signal sender or current_app fallback."""
    if sender is not None:
        return sender

    import celery as _celery

    return _celery.current_app


def _auto_setup_worker(sender, *, prefork: bool) -> None:
    """Shared worker setup path for both worker_init and process_init."""
    try:
        config = get_o11y_config()
        if not config.get("CELERY", {}).get("ENABLED", False):
            return

        app = _resolve_worker_app(sender)
        setup_celery_o11y(app, config)

        if prefork and config.get("PROFILING", {}).get("ENABLED"):
            if is_celery_fork_pool_worker():
                setup_profiling(config)
    except Exception:  # pragma: no cover
        logger.warning(
            "Failed to auto-setup django-o11y for Celery. "
            "Check your DJANGO_O11Y configuration.",
            exc_info=True,
        )


@_connect(
    worker_process_init,
    dispatch_uid="django_o11y.celery.worker_process_init",
)
def _auto_setup_on_worker_process_init(sender=None, **kwargs) -> None:
    """worker_process_init handler — runs setup in prefork child workers.

    Celery always fires this signal with ``sender=None``
    (see celery/concurrency/prefork.py).  Fall back to ``celery.current_app``
    so that ``setup_celery_o11y`` receives a real Celery instance.
    """
    if not is_celery_prefork_pool():
        return

    _auto_setup_worker(sender, prefork=True)


@_connect(
    worker_process_shutdown,
    dispatch_uid="django_o11y.celery.worker_process_shutdown",
)
def _auto_flush_on_worker_process_shutdown(sender=None, **kwargs) -> None:
    """worker_process_shutdown handler — flush spans before worker child exits."""
    try:
        config = get_o11y_config()
        if not config.get("CELERY", {}).get("ENABLED", False):
            return

        _maybe_force_flush(config, reason="worker_process_shutdown")
    except Exception:  # pragma: no cover
        logger.warning(
            "Failed to flush tracer provider during Celery worker shutdown.",
            exc_info=True,
        )
