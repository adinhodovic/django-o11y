"""Celery signal handlers that extend django-structlog with OpenTelemetry integration.

This module wraps django-structlog's CeleryReceiver to provide comprehensive
Celery task logging with additional OpenTelemetry tracing integration.
"""

import structlog
from celery import Celery
from django_structlog.celery.receivers import CeleryReceiver
from celery.signals import (
    after_task_publish,
    before_task_publish,
    task_failure,
    task_prerun,
    task_rejected,
    task_retry,
    task_revoked,
    task_success,
    task_unknown,
)


class ObservabilityCeleryReceiver(CeleryReceiver):
    """django-structlog CeleryReceiver subclass, reserved for future OTel-specific hooks."""

    pass


def setup_celery_signals(app: Celery) -> None:
    """Connect django-structlog's CeleryReceiver to all Celery task lifecycle signals."""
    receiver = ObservabilityCeleryReceiver()

    before_task_publish.connect(receiver.receiver_before_task_publish)
    after_task_publish.connect(receiver.receiver_after_task_publish)
    task_prerun.connect(receiver.receiver_task_prerun)
    task_success.connect(receiver.receiver_task_success)
    task_retry.connect(receiver.receiver_task_retry)
    task_failure.connect(receiver.receiver_task_failure)
    task_revoked.connect(receiver.receiver_task_revoked)
    task_rejected.connect(receiver.receiver_task_rejected)
    task_unknown.connect(receiver.receiver_task_unknown)

    logger = structlog.get_logger("django_observability.celery")
    logger.info("celery_signals_configured")
