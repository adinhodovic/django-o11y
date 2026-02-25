"""Pyroscope profiling setup and Celery profiling signal integration."""

import os
import socket
from typing import Any

from django_o11y.logging.utils import get_logger
from django_o11y.tracing.utils import (
    is_celery_fork_pool_worker,
    is_celery_prefork_pool,
)

logger = get_logger()


def setup_profiling(config: dict[str, Any]) -> None:
    """Configure Pyroscope with standard tags (service, version, env, host, pid)."""
    if config.get("CELERY", {}).get("ENABLED", False):
        import importlib

        try:
            importlib.import_module("django_o11y.profiling.signals")
        except ImportError:
            logger.warning(
                "CELERY.ENABLED is true but Celery is not installed. "
                "Install with: pip install django-o11y[celery]"
            )

    profiling_config = config.get("PROFILING", {})

    if not profiling_config.get("ENABLED"):
        return

    is_prefork_parent = is_celery_prefork_pool() and not is_celery_fork_pool_worker()
    if is_prefork_parent:
        logger.info(
            "django_o11y: skipping pyroscope.configure() in Celery prefork process "
            "parent; worker child processes initialize profiling post-fork"
        )
        return

    try:
        import pyroscope
    except ImportError:
        logger.warning(
            "django_o11y: profiling enabled but pyroscope-io is not installed. "
            "Run: pip install django-o11y[profiling]"
        )
        return

    tags = {
        "service_version": config.get("SERVICE_VERSION", "unknown"),
        "environment": config.get("ENVIRONMENT", "development"),
        "host": socket.gethostname(),
        "process_id": str(os.getpid()),
    }

    if config.get("NAMESPACE"):
        tags["service_namespace"] = config["NAMESPACE"]

    custom_tags = profiling_config.get("TAGS", {})
    if custom_tags:
        tags.update(custom_tags)

    try:
        pyroscope.configure(
            application_name=config["SERVICE_NAME"],
            server_address=profiling_config["PYROSCOPE_URL"],
            tags=tags,
        )
    except Exception as e:
        logger.warning("django_o11y: profiling configuration failed: %s", e)
        raise

    logger.info(
        "Profiling configured for %s, sending to %s",
        config["SERVICE_NAME"],
        profiling_config["PYROSCOPE_URL"],
    )
