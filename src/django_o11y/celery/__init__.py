"""Celery o11y integration."""

from django_o11y.celery.setup import (
    setup_celery_o11y,
)

__all__ = ["setup_celery_o11y"]
