"""URL configuration for tests."""

from django.http import HttpResponse, JsonResponse
from django.urls import path

from django_o11y import get_urls


def test_view(request):
    """Simple test view."""
    return HttpResponse("OK")


def trigger_view(request):
    """Dispatch an add task and return the task ID."""
    from tests.tasks import add

    x = int(request.GET.get("x", 1))
    y = int(request.GET.get("y", 2))
    task = add.delay(x, y)
    return JsonResponse({"task_id": task.id, "x": x, "y": y})


urlpatterns = [
    path("test/", test_view, name="test"),
    path("trigger/", trigger_view, name="trigger"),
] + get_urls()
