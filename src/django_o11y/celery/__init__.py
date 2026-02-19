"""Celery o11y integration."""

from django_o11y.celery.setup import (
    _auto_setup_on_worker_init,
    setup_celery_o11y,
)

__all__ = ["setup_celery_o11y"]

# Register signal handler for automatic setup when Celery workers start
# This allows zero-config Celery observability - just set CELERY.ENABLED = True
try:
    from celery.signals import worker_init

    worker_init.connect(_auto_setup_on_worker_init)
except ImportError:  # pragma: no cover
    # Celery not installed, skip signal registration
    pass
