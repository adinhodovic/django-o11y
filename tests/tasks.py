"""Test tasks for django-o11y e2e tracing tests."""

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="tests.add")
def add(x, y, order_id=None):
    """Adds two numbers — used for e2e tracing and logging tests.

    Performs DB operations so SQLite3 spans are visible in traces alongside
    the Celery task span.

    The Order (created by the web process) is updated to "completed" here,
    and a TaskResult is inserted — so django_model_inserts_total{model=
    "taskresult"} reflects worker activity, distinct from the web process's
    django_model_inserts_total{model="order"}.
    """
    from tests.models import Order, TaskResult

    log.info("task_started", x=x, y=y, order_id=order_id)
    result = x + y

    # UPDATE the order created by the web process
    if order_id:
        order = Order.objects.get(pk=order_id)
        order.status = "completed"
        order.save(update_fields=["status", "updated_at"])
        log.info("order_completed", order_id=order.id)
    else:
        order = Order.objects.first()

    # INSERT a TaskResult — worker-only model, tracked separately in Prometheus
    task_result = TaskResult.objects.create(
        task_id=add.request.id or "eager",
        order=order,
        result=result,
    )
    log.info(
        "task_completed",
        x=x,
        y=y,
        result=result,
        task_result_id=task_result.id,
    )

    return result
