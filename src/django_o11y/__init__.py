"""
django-o11y - Comprehensive OpenTelemetry observability for Django.

This package provides:
- Distributed tracing with OpenTelemetry
- Structured logging with Structlog + OTLP export
- Hybrid metrics (django-prometheus + OpenTelemetry)
- Celery integration
- Profiling support (Pyroscope)
"""

import os
import pathlib
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("django-o11y")
except PackageNotFoundError:
    __version__ = "unknown"


def _is_celery_worker() -> bool:
    import sys

    argv = sys.argv
    return bool(argv) and os.path.basename(argv[0]) == "celery" and "worker" in argv


def _is_prefork_web_server() -> bool:
    import sys

    return "gunicorn" in sys.modules or "uwsgi" in sys.modules


def _bool_env(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.lower() not in ("false", "0", "no", "off")


# Only create the multiproc dir when it will actually be used:
# - Gunicorn/uWSGI with prometheus enabled
# - Celery worker with both prometheus and celery metrics enabled
_need_multiproc = (
    _is_prefork_web_server()
    and _bool_env("DJANGO_O11Y_METRICS_PROMETHEUS_ENABLED", True)
) or (
    _is_celery_worker()
    and _bool_env("DJANGO_O11Y_METRICS_PROMETHEUS_ENABLED", True)
    and _bool_env("DJANGO_O11Y_CELERY_METRICS_ENABLED", True)
)
if _need_multiproc:
    _multiproc_dir = os.environ.get(
        "DJANGO_O11Y_METRICS_MULTIPROC_BASE_DIR"
    ) or os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if _multiproc_dir:
        os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", _multiproc_dir)
        pathlib.Path(_multiproc_dir).mkdir(parents=True, exist_ok=True)

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
