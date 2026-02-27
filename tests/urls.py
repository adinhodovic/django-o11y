"""URL configuration for tests."""

from django.http import HttpResponse, JsonResponse
from django.urls import path

from django_o11y import get_urls


def test_view(request):
    """Simple test view."""
    return HttpResponse("OK")


def trigger_view(request):
    """Dispatch an add task and return the task ID.

    Creates an Order in the web process (increments django_model_inserts_total
    {model="order"} in the Django registry), then hands off to the Celery
    worker which creates a TaskResult (increments the same counter with
    model="taskresult" in the worker registry).
    """
    import uuid

    from tests.models import Order
    from tests.tasks import add

    x = int(request.GET.get("x", 1))
    y = int(request.GET.get("y", 2))

    order = Order.objects.create(
        order_number=f"WEB-{uuid.uuid4().hex[:8].upper()}",
        customer_email="web@example.com",
        amount=x + y,
        status="pending",
    )
    task = add.delay(x, y, order_id=order.id)
    return JsonResponse({"task_id": task.id, "order_id": order.id, "x": x, "y": y})


urlpatterns = [
    path("test/", test_view, name="test"),
    path("trigger/", trigger_view, name="trigger"),
] + get_urls()
