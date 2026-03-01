"""Pyroscope profiling setup and Celery profiling signal integration."""

import os
import socket
from typing import Any

from django_o11y.logging.utils import get_logger
from django_o11y.tracing.utils import (
    is_celery_fork_pool_worker,
    is_celery_prefork_pool,
)
from django_o11y.utils.process import get_process_identity

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
            "parent; worker child processes initialize profiling post-fork [%s]",
            get_process_identity(),
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

    # RESOURCE_ATTRIBUTES (including OTEL_RESOURCE_ATTRIBUTES) are the base;
    # automatic attributes override them so runtime values are always accurate.
    resource_attrs = dict(config.get("RESOURCE_ATTRIBUTES", {}))
    tags = resource_attrs

    tags.update(
        {
            "service_version": config["SERVICE_VERSION"],
            "host": socket.gethostname(),
            "process_id": str(os.getpid()),
        }
    )

    if deployment_environment := resource_attrs.get("deployment.environment"):
        tags["environment"] = deployment_environment
    if service_namespace := resource_attrs.get("service.namespace"):
        tags["service_namespace"] = service_namespace

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
        "Profiling configured for %s, sending to %s [%s]",
        config["SERVICE_NAME"],
        profiling_config["PYROSCOPE_URL"],
        get_process_identity(),
    )
