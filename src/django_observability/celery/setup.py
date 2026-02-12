"""Setup module for Celery observability integration."""

from typing import Any

from celery import Celery

# Track if Celery has been instrumented to prevent double-instrumentation
_instrumented = False


def setup_celery_observability(
    app: Celery, config: dict[str, Any] | None = None
) -> None:
    """
    Set up tracing, logging, and metrics for Celery tasks.

    Called automatically on worker start when ``CELERY.ENABLED`` is True.
    Can also be called manually for explicit control.
    """
    global _instrumented

    if _instrumented:
        return

    if config is None:
        from django_observability.conf import get_observability_config

        config = get_observability_config()

    celery_config = config.get("CELERY", {})

    if not celery_config.get("ENABLED", False):
        return

    if celery_config.get("TRACING_ENABLED", True):
        _setup_celery_tracing()

    if celery_config.get("LOGGING_ENABLED", True):
        _setup_celery_logging(app)

    if celery_config.get("METRICS_ENABLED", True):
        _setup_celery_metrics(app)

    _instrumented = True


def _setup_celery_tracing() -> None:
    """Set up automatic tracing for Celery tasks."""
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
    except ImportError:
        import warnings

        warnings.warn(
            "Celery tracing is enabled but 'opentelemetry-instrumentation-celery' is not installed. "
            "Install it with: pip install opentelemetry-instrumentation-celery",
            UserWarning,
            stacklevel=3,
        )


def _setup_celery_logging(app: Celery) -> None:
    """Set up structured logging for Celery tasks via django-structlog signals."""
    from django_observability.celery.signals import setup_celery_signals

    setup_celery_signals(app)


def _setup_celery_metrics(app: Celery) -> None:
    """Set up metrics for Celery tasks."""
    pass


def _auto_setup_on_worker_init(sender, **kwargs) -> None:
    """worker_init signal handler that runs setup_celery_observability on the starting worker."""
    try:
        from django_observability.conf import get_observability_config

        config = get_observability_config()

        if config.get("CELERY", {}).get("ENABLED", False):
            setup_celery_observability(sender, config)
    except Exception:  # pragma: no cover
        import warnings

        warnings.warn(
            "Failed to auto-setup django-observability for Celery. "
            "Check your DJANGO_OBSERVABILITY configuration.",
            UserWarning,
        )
