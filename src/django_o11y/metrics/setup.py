"""Metrics setup for Django startup."""

import os
import pathlib

from django.conf import settings
from django.urls import Resolver404, resolve

from django_o11y.logging.utils import get_logger

logger = get_logger()


def setup_metrics_for_django(config: dict) -> None:
    """Log metrics configuration and warn if endpoint is not routed."""
    metrics = config["METRICS"]
    settings.PROMETHEUS_EXPORT_MIGRATIONS = metrics["EXPORT_MIGRATIONS"]

    if not metrics["PROMETHEUS_ENABLED"]:
        return

    # If PROMETHEUS_MULTIPROC_DIR is already set in the environment (e.g. via
    # Docker Compose or a pre-fork server that sets it before Django starts),
    # ensure the directory exists now — before model imports trigger
    # prometheus_client metric initialisation and try to write .db files.
    _ensure_existing_multiproc_dir()

    if is_prefork_web_server():
        _prepare_metrics_multiproc_dir(metrics)

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


def _ensure_existing_multiproc_dir() -> None:
    """Create PROMETHEUS_MULTIPROC_DIR if it is already set in the environment.

    prometheus_client switches to multiprocess mode as soon as the env var is
    present, so the directory must exist before the first metric object is
    created — which can happen during model import, before any signal handler
    runs.
    """
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir:
        pathlib.Path(multiproc_dir).mkdir(parents=True, exist_ok=True)


def is_prefork_web_server() -> bool:
    """Return True when running under a pre-fork web server (Gunicorn, uWSGI).

    Gunicorn and uWSGI import themselves before Django's AppConfig.ready()
    runs, so their top-level package will already be present in sys.modules.
    """
    import sys

    return "gunicorn" in sys.modules or "uwsgi" in sys.modules


def _prepare_metrics_multiproc_dir(metrics: dict) -> None:
    """Set PROMETHEUS_MULTIPROC_DIR for pre-fork web server workers.

    Must be called in the parent process before forking so that:
    - The directory exists when children are forked.
    - The env var is inherited by all child processes.

    Each forked child re-sets the var via the post-fork hook in fork.py.
    """
    multiproc_dir = metrics["MULTIPROC_DIR"]
    pathlib.Path(multiproc_dir).mkdir(parents=True, exist_ok=True)
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = multiproc_dir
    logger.info("Prometheus multiprocess metrics dir: %s", multiproc_dir)
