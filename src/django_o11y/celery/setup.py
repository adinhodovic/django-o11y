"""Setup module for Celery o11y integration."""

import os
import sys
import warnings
from typing import Any

from celery import Celery

from django_o11y.celery.signals import setup_celery_signals
from django_o11y.conf import get_o11y_config
from django_o11y.tracing.provider import setup_tracing

# Track instrumentation per-process to remain fork-safe.
_instrumented_pid: int | None = None


def _is_celery_worker_boot(argv: list[str] | None = None) -> bool:
    """Return True when the current process is a ``celery worker`` invocation.

    Handles all common forms::

        celery -A proj worker
        /usr/local/bin/celery -A proj worker
        python -m celery -A proj worker
    """
    args = argv if argv is not None else sys.argv

    if not args or "worker" not in args:
        return False

    cmd = os.path.basename(args[0])
    is_celery_cmd = cmd == "celery"
    is_python_module = any(
        arg == "-m" and idx + 1 < len(args) and args[idx + 1] == "celery"
        for idx, arg in enumerate(args)
    )
    return is_celery_cmd or is_python_module


def _is_celery_prefork_pool(argv: list[str] | None = None) -> bool:
    """Return True when Celery worker is running with prefork pool.

    Celery defaults to prefork when no explicit pool is passed.
    Returns False when the process is not a ``celery worker`` at all.
    """
    args = argv if argv is not None else sys.argv

    if not _is_celery_worker_boot(args):
        return False

    for idx, arg in enumerate(args):
        if arg.startswith("--pool="):
            return arg.split("=", 1)[1] == "prefork"
        if arg in {"-P", "--pool"} and idx + 1 < len(args):
            return args[idx + 1] == "prefork"

    return True


def setup_celery_o11y(app: Celery, config: dict[str, Any] | None = None) -> None:
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

    app.conf.worker_send_task_events = True
    app.conf.task_send_sent_event = True

    if config.get("TRACING", {}).get("ENABLED") and celery_config.get(
        "TRACING_ENABLED", True
    ):
        setup_tracing(config)
        _setup_celery_tracing()

    if celery_config.get("LOGGING_ENABLED", True):
        setup_celery_signals(app)
        _setup_celery_logging()

    _instrumented_pid = os.getpid()


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
