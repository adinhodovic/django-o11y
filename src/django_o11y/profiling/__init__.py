"""Pyroscope profiling integration with proper tags."""

import logging
import os
import socket
from typing import Any

logger = logging.getLogger("django_o11y.profiling")


def _is_celery_prefork_boot(argv: list[str] | None = None) -> bool:
    """Return True when current process is a celery prefork worker boot."""
    from django_o11y.celery.detection import is_celery_prefork_pool

    return is_celery_prefork_pool(argv)


def setup_profiling(config: dict[str, Any]) -> None:
    """Configure Pyroscope with standard tags (service, version, env, host, pid).

    Skips ``pyroscope.configure()`` for Celery prefork parent and child
    processes to avoid fork-safety issues in native profilers.
    Context: https://github.com/grafana/pyroscope-rs/issues/276
    """
    profiling_config = config.get("PROFILING", {})

    if not profiling_config.get("ENABLED"):
        return

    if _is_celery_prefork_boot():
        logger.info(
            "django_o11y: skipping pyroscope.configure() in Celery prefork process "
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
