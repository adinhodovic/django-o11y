"""Celery profiling signal handlers."""

from celery.signals import worker_process_init

from django_o11y.config.setup import get_o11y_config
from django_o11y.logging.utils import get_logger
from django_o11y.tracing.utils import is_celery_fork_pool_worker, is_celery_prefork_pool
from django_o11y.utils.signals import connect_signal

logger = get_logger()


@connect_signal(
    worker_process_init,
    dispatch_uid="django_o11y.profiling.worker_process_init",
)
def _auto_setup_profiling_on_worker_process_init(sender=None, **kwargs) -> None:
    """Initialize profiling in prefork child workers post-fork."""
    if not is_celery_prefork_pool() or not is_celery_fork_pool_worker():
        return

    try:
        config = get_o11y_config()
        if not config.get("CELERY", {}).get("ENABLED", False):
            return

        if not config.get("PROFILING", {}).get("ENABLED", False):
            return

        from django_o11y.profiling.setup import setup_profiling

        setup_profiling(config)
    except Exception:  # pragma: no cover
        logger.warning(
            "Failed to auto-setup django-o11y profiling for Celery.",
            exc_info=True,
        )
