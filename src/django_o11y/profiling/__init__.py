"""Pyroscope profiling integration with proper tags."""

import logging
import os
import socket
from typing import Any

from django_o11y.tracing.provider import _is_celery_fork_pool_worker

logger = logging.getLogger("django_o11y.profiling")


def setup_profiling(config: dict[str, Any]) -> None:
    """Configure Pyroscope with standard tags (service, version, env, host, pid).

    Skips ``pyroscope.configure()`` inside Celery prefork worker children to
    avoid fork-safety issues with the pyroscope-io SDK.  Traces are still
    emitted by the worker; only the profile→trace correlation span processor
    is also skipped (see ``tracing.provider.setup_tracing``).
    """
    profiling_config = config.get("PROFILING", {})

    if not profiling_config.get("ENABLED"):
        return

    if _is_celery_fork_pool_worker():
        logger.info(
            "django_o11y: skipping pyroscope.configure() in Celery prefork worker "
            "(fork-safety); traces still active"
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

    # service_name is already set via application_name; including it here
    # produces a duplicate label that Pyroscope rejects with 400.
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
