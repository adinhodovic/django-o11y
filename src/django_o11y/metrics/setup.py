"""Metrics setup for Django startup."""

from django.conf import settings
from django.urls import Resolver404, resolve

from django_o11y.logging.utils import get_logger

logger = get_logger()


def setup_metrics_for_django(config: dict) -> None:
    """Log metrics configuration and warn if endpoint is not routed."""
    metrics = config.get("METRICS", {})
    settings.PROMETHEUS_EXPORT_MIGRATIONS = metrics.get("EXPORT_MIGRATIONS", True)

    if not metrics.get("PROMETHEUS_ENABLED", True):
        return

    endpoint = metrics.get("PROMETHEUS_ENDPOINT", "/metrics")
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
