"""django-o11y: OpenTelemetry-based observability for Django."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("django-o11y")
except PackageNotFoundError:
    __version__ = "unknown"


def get_urls() -> list:
    """Return django-o11y URL patterns.

    This currently adds the Prometheus metrics route based on
    ``METRICS.PROMETHEUS_ENDPOINT``. Returns an empty list when
    ``METRICS.PROMETHEUS_ENABLED`` is ``False``.
    """
    from django.urls import path
    from django_prometheus import exports

    from django_o11y.config.setup import get_config

    config = get_config()
    metrics = config.get("METRICS", {})

    if not metrics.get("PROMETHEUS_ENABLED", True):
        return []

    endpoint = metrics["PROMETHEUS_ENDPOINT"].lstrip("/")
    return [
        path(
            endpoint,
            exports.ExportToDjangoView,
            name="prometheus-django-metrics",
        )
    ]
