"""Test tasks for django-o11y e2e tracing tests."""

import uuid

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="tests.add")
def add(x, y):
    """Adds two numbers — used for e2e tracing and logging tests.

    Also performs DB read/write operations so SQLite3 spans are visible
    in traces alongside the Celery task span.
    """
    from tests.models import Order

    log.info("task_started", x=x, y=y)
    result = x + y

    # INSERT — creates a traceable DB span
    order = Order.objects.create(
        order_number=f"TASK-{uuid.uuid4().hex[:8].upper()}",
        customer_email="tracing@example.com",
        amount=result,
        status="processing",
    )
    log.info("order_created", order_id=order.id, order_number=order.order_number)

    # SELECT — second DB span
    order = Order.objects.get(pk=order.pk)

    # UPDATE — third DB span
    order.status = "completed"
    order.save(update_fields=["status", "updated_at"])
    log.info("task_completed", x=x, y=y, result=result, order_id=order.id)

    return result
