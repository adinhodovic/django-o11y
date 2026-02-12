"""URL configuration for tests."""

from django.urls import path


def test_view(request):
    """Simple test view."""
    from django.http import HttpResponse

    return HttpResponse("OK")


urlpatterns = [
    path("test/", test_view, name="test"),
]
