"""URL configuration for tests."""

from django.urls import path

from django_o11y import get_urls


def test_view(request):
    """Simple test view."""
    from django.http import HttpResponse

    return HttpResponse("OK")


urlpatterns = [
    path("test/", test_view, name="test"),
] + get_urls()
