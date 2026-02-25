"""Celery tracing signal handlers."""

from typing import Any

from celery.signals import worker_init, worker_process_init, worker_process_shutdown

from django_o11y.config.setup import get_o11y_config
from django_o11y.logging.utils import get_logger
from django_o11y.tracing.utils import is_celery_prefork_pool
from django_o11y.utils.signals import connect_signal

logger = get_logger()


def _maybe_force_flush(config: dict[str, Any], reason: str) -> None:
    """Flush pending spans from current process provider."""
    if not config.get("TRACING", {}).get("ENABLED", False):
        return

    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        logger.warning(
            "Failed to force-flush tracer provider on %s", reason, exc_info=True
        )


def _resolve_worker_app(sender):
    """Resolve Celery app from signal sender or current_app fallback."""
    if sender is not None:
        return sender

    import celery as _celery

    return _celery.current_app


def _auto_setup_worker(sender) -> None:
    """Shared worker setup path for both worker_init and process_init."""
    try:
        config = get_o11y_config()
        if not config.get("CELERY", {}).get("ENABLED", False):
            return

        app = _resolve_worker_app(sender)
        from django_o11y.tracing.setup import setup_celery_o11y

        setup_celery_o11y(app, config)
    except Exception:  # pragma: no cover
        logger.warning(
            "Failed to auto-setup django-o11y tracing for Celery. "
            "Check your DJANGO_O11Y configuration.",
            exc_info=True,
        )


@connect_signal(worker_init, dispatch_uid="django_o11y.tracing.worker_init")
def _auto_setup_on_worker_init(sender, **kwargs) -> None:
    """worker_init signal handler - runs setup on non-prefork workers."""
    if is_celery_prefork_pool():
        return

    _auto_setup_worker(sender)


@connect_signal(
    worker_process_init, dispatch_uid="django_o11y.tracing.worker_process_init"
)
def _auto_setup_on_worker_process_init(sender=None, **kwargs) -> None:
    """worker_process_init handler - runs setup in prefork child workers."""
    if not is_celery_prefork_pool():
        return

    _auto_setup_worker(sender)


@connect_signal(
    worker_process_shutdown,
    dispatch_uid="django_o11y.tracing.worker_process_shutdown",
)
def _auto_flush_on_worker_process_shutdown(sender=None, **kwargs) -> None:
    """worker_process_shutdown handler - flush spans before worker child exits."""
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
