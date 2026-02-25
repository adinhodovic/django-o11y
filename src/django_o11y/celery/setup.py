"""Setup module for Celery o11y integration."""

import os
import warnings
from typing import TYPE_CHECKING, Any

from django_o11y.celery.detection import (
    is_celery_prefork_pool,
    is_celery_worker_boot,
)
from django_o11y.conf import get_o11y_config
from django_o11y.tracing.provider import setup_tracing

if TYPE_CHECKING:  # pragma: no cover
    from celery import Celery

# Track instrumentation per-process to remain fork-safe.
_instrumented_pid: int | None = None
_early_logging_hook_registered = False


def _is_celery_worker_boot(argv: list[str] | None = None) -> bool:
    """Compatibility wrapper for shared celery worker boot detection."""
    return is_celery_worker_boot(argv)


def _is_celery_prefork_pool(argv: list[str] | None = None) -> bool:
    """Compatibility wrapper for shared celery prefork pool detection."""
    return is_celery_prefork_pool(argv)


def setup_celery_o11y(app: "Celery", config: dict[str, Any] | None = None) -> None:
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

    _setup_django_structlog_worker_step(app)

    if config.get("TRACING", {}).get("ENABLED") and celery_config.get(
        "TRACING_ENABLED", True
    ):
        setup_tracing(config)
        _setup_celery_tracing()

    _instrumented_pid = os.getpid()


def register_early_celery_logging_hook() -> None:
    """Hook Celery's setup_logging signal so workers use Django's LOGGING config.

    Without this, Celery configures its own logging on worker startup and the
    worker process ends up with a different format (plain text) from the Django
    process (structlog JSON/console).  Connecting to ``setup_logging`` and
    calling ``dictConfig(settings.LOGGING)`` replicates the pattern described
    in the logging blog post.
    """
    global _early_logging_hook_registered

    if _early_logging_hook_registered:
        return

    import logging.config as _logging_config

    from celery.signals import setup_logging
    from django.conf import settings

    @setup_logging.connect(weak=False, dispatch_uid="django_o11y.celery.setup_logging")
    def _config_loggers(*args, **kwargs):  # pylint: disable=unused-variable
        if hasattr(settings, "LOGGING") and settings.LOGGING:
            _logging_config.dictConfig(settings.LOGGING)
            # Returning truthy tells Celery to skip its own logger setup.
            return True
        return False

    _early_logging_hook_registered = True


def _setup_django_structlog_worker_step(app: "Celery") -> None:
    """Register django-structlog worker init step when available."""
    try:
        from django_structlog.celery.steps import DjangoStructLogInitStep
    except ImportError:
        return

    app.steps["worker"].add(DjangoStructLogInitStep)


def _setup_celery_tracing() -> None:
    """Set up automatic tracing for Celery tasks.

    In Celery prefork workers the parent Django process already called
    ``CeleryInstrumentor().instrument()`` (via instrumentation/setup.py) to
    inject W3C traceparent headers on the producer side.  That sets the
    class-level ``_is_instrumented_by_opentelemetry = True`` which every
    forked child inherits.  Calling ``instrument()`` again in each child
    triggers the "Attempting to instrument while already instrumented" warning
    from the OTel SDK even though the monkey-patches are already in place.

    The TracerProvider is re-created per-child by ``setup_tracing()`` before
    this function is called, so we only need to skip re-patching here.
    """
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        instrumentor = CeleryInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
    except ImportError:
        warnings.warn(
            "Celery tracing is enabled but 'opentelemetry-instrumentation-celery' "
            "is not installed. "
            "Install it with: pip install opentelemetry-instrumentation-celery",
            UserWarning,
            stacklevel=3,
        )


def _auto_setup_on_worker_init(sender, **kwargs) -> None:
    """worker_init signal handler — runs setup_celery_o11y on worker start."""
    if _is_celery_prefork_pool():
        return

    try:
        config = get_o11y_config()

        if config.get("CELERY", {}).get("ENABLED", False):
            setup_celery_o11y(sender, config)
    except Exception:  # pragma: no cover
        warnings.warn(
            "Failed to auto-setup django-o11y for Celery. "
            "Check your DJANGO_O11Y configuration.",
            UserWarning,
            stacklevel=2,
        )


def _auto_setup_on_worker_process_init(sender=None, **kwargs) -> None:
    """worker_process_init handler — runs setup in prefork child workers.

    Celery always fires this signal with ``sender=None``
    (see celery/concurrency/prefork.py).  Fall back to ``celery.current_app``
    so that ``setup_celery_o11y`` receives a real Celery instance.
    """
    if not _is_celery_prefork_pool():
        return

    try:
        config = get_o11y_config()

        if config.get("CELERY", {}).get("ENABLED", False):
            app = sender
            if app is None:
                import celery as _celery

                app = _celery.current_app
            setup_celery_o11y(app, config)
    except Exception:  # pragma: no cover
        warnings.warn(
            "Failed to auto-setup django-o11y for Celery. "
            "Check your DJANGO_O11Y configuration.",
            UserWarning,
            stacklevel=2,
        )
