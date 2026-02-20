"""Setup module for Celery o11y integration."""

import warnings
from typing import Any

from celery import Celery

from django_o11y.celery.signals import setup_celery_signals
from django_o11y.conf import get_o11y_config

# Track if Celery has been instrumented to prevent double-instrumentation
_instrumented = False


def setup_celery_o11y(app: Celery, config: dict[str, Any] | None = None) -> None:
    """
    Set up tracing, logging, and metrics for Celery tasks.

    Called automatically on worker start when ``CELERY.ENABLED`` is True.
    Can also be called manually for explicit control.
    """
    global _instrumented

    if _instrumented:
        return

    if config is None:
        config = get_o11y_config()

    celery_config = config.get("CELERY", {})

    if not celery_config.get("ENABLED", False):
        return

    # Enable task events so celery-exporter can receive them via the broker.
    # worker_send_task_events enables per-task state events from the worker.
    # task_send_sent_event additionally emits the SENT state from the client
    # side, allowing celery-exporter to show the delta between sent and
    # received tasks.
    app.conf.worker_send_task_events = True
    app.conf.task_send_sent_event = True

    if celery_config.get("TRACING_ENABLED", True):
        _setup_celery_tracing()

    if celery_config.get("LOGGING_ENABLED", True):
        setup_celery_signals(app)
        _setup_celery_logging()

    _instrumented = True


def _setup_celery_logging() -> None:
    """Hook Celery's setup_logging signal so workers use Django's LOGGING config.

    Without this, Celery configures its own logging on worker startup and the
    worker process ends up with a different format (plain text) from the Django
    process (structlog JSON/console).  Connecting to ``setup_logging`` and
    calling ``dictConfig(settings.LOGGING)`` replicates the pattern described
    in the logging blog post.
    """
    import logging.config as _logging_config

    from celery.signals import setup_logging
    from django.conf import settings

    @setup_logging.connect(weak=False)
    def _config_loggers(*args, **kwargs):  # pylint: disable=unused-variable
        if hasattr(settings, "LOGGING") and settings.LOGGING:
            _logging_config.dictConfig(settings.LOGGING)


def _setup_celery_tracing() -> None:
    """Set up automatic tracing for Celery tasks."""
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
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
