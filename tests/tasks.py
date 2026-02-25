"""Test tasks for django-o11y e2e tracing tests."""

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="tests.add")
def add(x, y):
    """Adds two numbers — used for e2e tracing and logging tests."""
    log.info("task_started", x=x, y=y)
    result = x + y
    log.info("task_completed", x=x, y=y, result=result)
    return result
