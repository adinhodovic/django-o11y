"""Metrics setup during Django startup."""

from django.conf import settings
from django.urls import Resolver404, resolve

from django_o11y.logging.utils import get_logger

logger = get_logger()


def setup_metrics_for_django(config: dict) -> None:
    """Log metrics setup and warn when the endpoint is not routed."""
    metrics = config["METRICS"]
    settings.PROMETHEUS_EXPORT_MIGRATIONS = metrics["EXPORT_MIGRATIONS"]

    if not metrics["PROMETHEUS_ENABLED"]:
        return

    endpoint = metrics["PROMETHEUS_ENDPOINT"]
    logger.info("Metrics enabled at %s", endpoint)

    normalized = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    try:
        resolve(normalized)
    except Resolver404:
        logger.warning(
            "Metrics endpoint %s is not routed. Add `+ get_urls()` to your "
            "root urlpatterns.",
            normalized,
        )


def is_prefork_web_server() -> bool:
    """Return ``True`` when running under a pre-fork web server.

    Gunicorn and uWSGI import their top-level packages before
    ``AppConfig.ready()`` runs, so they are present in ``sys.modules``.
    """
    import sys

    return "gunicorn" in sys.modules or "uwsgi" in sys.modules
