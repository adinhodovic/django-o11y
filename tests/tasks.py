"""Test tasks for django-o11y e2e tracing tests."""

from celery import shared_task


@shared_task(name="tests.add")
def add(x, y):
    """Simple task that adds two numbers — used for e2e tracing tests."""
    return x + y
