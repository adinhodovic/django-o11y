"""
django-o11y - Comprehensive OpenTelemetry observability for Django.

This package provides:
- Distributed tracing with OpenTelemetry
- Structured logging with Structlog + OTLP export
- Hybrid metrics (django-prometheus + OpenTelemetry)
- Celery integration
- Profiling support (Pyroscope)
"""

__version__ = "0.2.0"

default_app_config = "django_o11y.apps.DjangoO11yConfig"


def get_urls() -> list:
    """Return URL patterns for django-o11y managed routes.

    Currently includes the Prometheus metrics endpoint, respecting
    ``METRICS.PROMETHEUS_ENDPOINT`` (default ``/metrics``). Returns an
    empty list when ``METRICS.PROMETHEUS_ENABLED`` is ``False``.

    Example::

        # urls.py
        from django_o11y import get_urls

        urlpatterns = [
            path("admin/", admin.site.urls),
            ...
        ] + get_urls()
    """
    from django.urls import include, path

    from django_o11y.conf import get_config

    config = get_config()
    metrics = config.get("METRICS", {})

    if not metrics.get("PROMETHEUS_ENABLED", True):
        return []

    endpoint = metrics.get("PROMETHEUS_ENDPOINT", "/metrics").lstrip("/")
    return [path(endpoint, include("django_prometheus.urls"))]
